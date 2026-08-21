---
id: ADR-405
type: adr
title: "Retenção de artefato é per-produtor: recência só autoriza expurgo em stage determinístico"
status: Proposto
date: "2026-08-21"
relates_to:
  - "[[ADR-157]]"
  - "[[ADR-171]]"
  - "[[ADR-212]]"
  - "[[ADR-231]]"
  - "[[ADR-311]]"
  - "[[ADR-371]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 405"
  - "retenção per-produtor"
  - "superseded não autoriza delete"
tags:
  - area/dados
  - status/proposto
  - type/adr
---

# ADR-405 — Retenção de artefato é per-produtor

**Status:** Proposto · **Data:** 2026-08-21

## Contexto

A política de retenção de `pipeline_artifacts` (A33.l6, sob [[ADR-212]]) apaga
row *superseded* com mais de 180 dias. Ela carrega uma premissa que nunca foi
escrita: **a versão corrente domina as anteriores**, logo o histórico é
redundante.

Essa premissa é aproximadamente verdadeira para produtor determinístico e
**falsa** para stage LLM. Medido em 2026-08-21 no corpus de dogfood
(16.292 artifacts): `extract_irpf_full` ([[ADR-157]]) re-extrai o **mesmo**
documento com resultados diferentes. Em 77 versões de um mesmo `artifact_key`,
`rendimentos_tributacao_exclusiva` alterna entre 11 e 3 itens — **10 rodadas
em 11, 9 rodadas em 3, sob a mesma `prompt_version=1.2.0` e o mesmo
`schema_version`** (colunas de `pipeline_artifacts`, não campos do payload).
`pagamentos_efetuados` alterna entre 5 e 1.

As versões antigas não são cópias piores da corrente. São **sorteios
diferentes da mesma distribuição**, e o histórico é o único registro de que a
distribuição existe.

Dois desdobramentos medidos:

- **A corrente não é autoritativa.** `_get_latest_in_workspace` devolve o
  último sorteio. Dois artefatos de IRPF estão hoje com a versão corrente
  degradada: um com 0 de 2 `pagamentos_efetuados` (0% do valor de pico) e
  outro com 1 de 5 (2,6%). O relatório publicado usa essas.
- **Duas classes de divergência, não uma.** Em
  `rendimentos_tributacao_exclusiva` a soma em BRL é **idêntica** entre os
  modos de 11 e de 3 itens, e os `codigo_rfb` distintos se preservam: é perda
  de granularidade, e os buckets do E5 (que pescam por código) sobrevivem. Em
  `pagamentos_efetuados` a soma cai **97,4%**: é perda de valor. Um detector
  único trata as duas como "flapping" e declara ambas fechadas ao consertar
  uma.

## Decisão

**Recência autoriza expurgo apenas conjugada a uma afirmação de determinismo
do produtor.** O corpus se particiona:

| Classe | Stages | Política |
| --- | --- | --- |
| Determinístico | parsers E2, `reconcile_transactions`, `categorize_transactions`, `consolidate_baseline` | expurgo por idade, como hoje |
| Não-determinístico (LLM) | `extract_irpf_full`, `E1.5a`, `extract_informes_anuais`, `extract_comprovantes_bens`, `extract_informe_aluguel`, `extract_with_llm`, `review_finances_holistic` | **retém o histórico** enquanto o não-determinismo não estiver fechado |

Consequências que esta ADR fixa:

1. **`prune_mode` não flippa para `delete`** antes de a partição existir em
   código. Hoje o flip apagaria histórico de stage LLM junto com o resto.
2. **Não existe mecanismo de preservação seletiva.** `retention_until = NULL`
   em row superseded é revertido por `_mark_group` na execução diária
   seguinte — `NULL` é fail-safe só para a **corrente**. Qualquer plano que
   diga "estas ficam" precisa antes de uma coluna de hold ou desta partição.
   Foi por isso que a proposta de preservar 21 rows e deletar 397 foi
   recusada: era intenção sem mecanismo.
3. **Predicado de contenção não autoriza deleção irreversível.** Sobre os
   mesmos 418 artifacts, três predicados defensáveis deram três respostas:
   `len(lista)` = 397 contidos, superset-de-escalares = 254, identidade exata
   do item = 87 — fator 4,5× entre os extremos, e 27 dos 418 passam por
   vacuidade (nenhuma lista de topo não-vazia). Quando a escolha do predicado
   decide o que se apaga, não há medição: há premissa com aparência de número.
   O predicado permanece válido como **detector de instabilidade** — foi assim
   que a oscilação apareceu — e inválido como autorização de expurgo.
4. **Expurgo nomeado, quando necessário, é service explícito** em
   `backend/app/services/internal_ops/` no padrão de `pipeline_reset`: lista
   de ids por predicado nomeado, consulta a `referenced_artifact_ids`
   ([[ADR-371]] D3), preview → confirmação → audit. **Nunca** por backdating
   de `retention_until`, que destrói a única verificação gratuita da coluna
   (hoje ela é recomputável como `successor.created_at + superseded_days`).

## Débito nomeado, não resolvido aqui

- **O relógio de `retention_until` tem dois escritores que discordam.**
  `_mark_superseded_previous` usa `datetime.now()`; `_mark_group` usa
  `successor.created_at`. Quem marcou o corpus foi o write-path — daí
  **6.502 rows (42,2%) vencerem no mesmo dia, 2027-01-04**, com sucessores
  nascidos entre maio e julho. O docstring de `artifact_prune.py` afirma o
  oposto ("o relógio conta do momento real de supersessão, não do deploy"):
  verdade sobre o backfill, falso sobre o caminho que marcou o corpus.
- **`run_artifact_prune` faz backfill e delete na mesma transação**, sem gate
  entre os dois. Latente hoje (0 rows expiradas), estrutural sempre.
- **O beat de prune não roda no dogfood** (508 superseded ainda com
  `retention_until` NULL) — o dry-run que deveria calibrar a política nunca
  produziu relatório real.
- **Calibração na distribuição errada.** O corpus tem ~74 re-runs por chave em
  3 meses (p50 de `extract_statements` e `extract_invoices`). Um workspace de
  produção terá punhados. Política calibrada aqui não transfere.
- **O não-determinismo em si** é escopo de `prompt-engineer` + `senior-cto`,
  não desta ADR. Enquanto vigorar, nenhuma política de retenção sobre stage
  LLM é defensável.

## Alternativas consideradas

- **Deletar os 418 em plaintext (recência pura).** Recusada: são 3,39 MB de
  316,97 MB — **1,07% do corpus**. O ganho é de armazenamento e é desprezível;
  o custo é destruir a evidência do não-determinismo, descoberto exatamente
  por comparar essas rows. Precedente direto: [[ADR-371]] §Alternativas já
  recusou "limpar o DB de dogfood primeiro" com este mesmo argumento.
- **Endurecer o predicado de contenção.** Recusada: o custo de provar
  contenção item-a-item através de evolução de schema e produtor
  não-determinístico excede o valor da deleção que ele autorizaria.
- **Retenção uniforme mais longa.** Recusada: não separa as duas classes, e é
  a separação que carrega a decisão.

## Referências

- [[ADR-212]] §W6-T05 — política de retenção que esta ADR emenda.
- [[ADR-231]] — encryption at-rest; a disposição dos 418 (cifrar, não deletar)
  está registrada na emenda de 2026-08-21 lá.
- [[ADR-171]] — gate de rotação; `skipped` não é evidência (emenda de
  2026-08-21).
- [[ADR-157]] — `extract_irpf_full`, o stage onde o não-determinismo foi medido.
- [[ADR-311]] / [[ADR-371]] — tombstone e grafo de FK como fonte da deleção.
