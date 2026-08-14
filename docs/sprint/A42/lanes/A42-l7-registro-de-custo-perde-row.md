---
id: A42.l7
type: lane
title: "Registro de custo de LLM é fonte de verdade que perde row e vaza identificador de documento"
sprint: A42
status: planned
priority: P1
branch_slug: a42-l7-registro-de-custo-perde-row
adrs:
  - "[[ADR-173]]"
  - "[[ADR-357]]"
  - "[[ADR-371]]"
depends_on: []
tags:
  - type/lane
  - sprint/a42
  - status/planned
  - priority/p1
  - area/dados
  - area/llm
---

# A42.l7 — `registro-de-custo-perde-row` (RV4-03, RV4-14, RV4-22, RV4-42, RV4-52)

> **Origem:** [[PIPELINE-REVIEWS-active]] §r4 2026-08-04 — RV4-03 (Alto, **provado em
> Postgres real**), RV4-14, RV4-22, RV4-42, RV4-52.

> **Depende de [[A40.l19]] — quitada 2026-08-14.** A l19 shipou (#1241). A razão
> (duas migrations concorrentes ramificam a cadeia) está satisfeita: esta lane é
> a próxima na cadeia, em PR próprio, sem misturar com feature. `depends_on`
> saiu. `LLMCallLog.stage` segue `String(64)` (`llm_call_log.py:26`).

## Problema

A tabela que registra custo de LLM é a **fonte única de verdade** do hard-stop de
orçamento da [[ADR-173]]. Ela perde row por cinco caminhos independentes:

1. **Coluna curta.** O campo de stage é limitado, e dois produtores interpolam o nome
   do arquivo nele. A chave estoura, o banco levanta truncamento, **a exceção é
   engolida em aviso** e a row de custo desaparece. Verificado em Postgres real: hoje
   não morde porque o ambiente de desenvolvimento não é Postgres — **realiza-se no
   cutover**.
2. **Contenção do banco local** faz um stage multi-documento registrar uma row de N,
   e a verdade em memória nunca é reconciliada contra a fonte única.
3. **Retentativa cobrada e invisível:** a retentativa do cliente é cobrada pelo
   provedor, o uso reportado vem só da última resposta, o ramo de exceção não registra
   nada e não há coluna de tentativa. O orçamento opera sobre **piso**, não sobre gasto.
4. **Skip incremental grava status de concluído** com marcador de skip, enquanto skip
   de LLM grava status próprio. "N de N stages concluídos" **não é sinal de trabalho
   feito** — e é o denominador da própria afirmação de execução do relatório.
5. **Vazamento:** o campo de stage carrega o nome canônico do documento (com código de
   instituição) numa tabela classificada no export de privacidade como **sem dado
   pessoal**.

O item 1 e o item 5 têm o **mesmo fix** (nome de stage descritivo puro, sem
interpolação), e há precedente de correção já aplicada noutro módulo.

## Decisão

1. **Migration** que amplia a coluna, em PR próprio, **depois** da [[A40.l19]]
   (#1241) na cadeia — não mais "atrás de alguém em voo".
2. **Nome de stage descritivo puro** nos dois produtores que interpolam filename —
   fecha 1 e 5 juntos. Identificar o documento, se necessário, em coluna própria.
3. **Falha de escrita do registro de custo não pode ser engolida em aviso.** É a fonte
   de verdade de um hard-stop: perder row silenciosamente derrota o mecanismo. Falhar
   alto ou registrar a falha de forma contável.
4. **Coluna de tentativa** e registro por tentativa no ponto único de chamada, para o
   orçamento medir gasto e não piso.
5. **Propagar o retorno do stage para o enum que os leitores consultam**, para que
   skip não se apresente como trabalho concluído.
6. **Reconciliar a verdade em memória contra a fonte única** ao fim do run, com a
   divergência reportada.
7. **Decidir se `llm_call_log.pipeline_run_id` vira FK de verdade.** Hoje é
   `String(36)` indexado, **sem `ForeignKey`** — referência solta. A [[ADR-371]]
   §D7 ligou o gate `dev/check_run_artifact_fk_coverage.py`, que exige FK ou
   justificativa; a coluna entrou no allowlist com a premissa *"telemetria de
   custo sobrevive de propósito ao run, porque FinOps agrega por período e
   cascatear apagaria o histórico"*. Essa premissa foi **herdada do código, não
   verificada com o dono** — e esta lane é quem tem o contexto (é a dona do
   hard-stop de orçamento) e já abre migration nessa tabela. Ou confirma o
   allowlist com a razão registrada, ou adiciona a FK com o `ondelete` que a
   retenção de custo exigir (provavelmente `SET NULL`, não `CASCADE`).

## Critério de aceite

- Teste de regressão **antes** do fix, em Postgres (não no banco local): nome de
  stage longo ⇒ row persistida, nunca perdida. Hoje desaparece.
- Nenhum produtor interpola nome de arquivo no campo de stage — grep prova; e o
  export de privacidade volta a ser verdadeiro para essa tabela.
- Falha de escrita no registro de custo **não** passa por aviso silencioso: teste que
  injeta falha e exige que ela seja contável.
- Retentativa aparece como row própria ou com contador de tentativa; o total do run
  reconcilia com o que o provedor cobraria.
- Stage que fez skip **não** reporta status de concluído. Teste sobre run incremental.
- Reconciliação memória ↔ fonte única ao fim do run, com divergência diferente de
  zero falhando o run em modo estrito.
- **Migration em PR próprio**, encadeada depois da [[A40.l19]] (#1241); cadeia
  de revisão linear verificada antes do merge.
