---
id: A40.l117
type: lane
title: "O parecer publica dois números para a mesma coisa, cita a seção errada em 4 de 11 riscos, e o prompt se contradiz sobre ter ferramentas"
sprint: A40
plan: PLAN-report-trust
status: open
priority: P1
branch_slug: a40-l117-parecer-dois-numeros-e-citacao-desorientada
owner: prompt-engineer
depends_on: []
adrs: ["[[ADR-199]]"]
tags: [type/lane, sprint/a40, status/open, priority/p1, area/backend]
---

# A40.l117 — `parecer-dois-numeros-e-citacao-desorientada`

> **Origem:** `RR9-08` + `RR9-11` + `RR9-14` da rodada unificada **U5**
> ([[PIPELINE-REVIEWS-active]] §r13). Três sintomas com a mesma raiz: **prosa autoral do
> modelo não passa por invariante**.

## Os três sintomas

1. **Dois valores para "renda fixa na carteira" na mesma seção**, com **4,15 pp** de
   spread: um autoral do modelo, o outro carimbado pela máquina. Nada reconcilia porque
   `parecer_prose_money.py:16` declara que **percentuais ficam fora** do invariante —
   medido: **27 percentuais em 47 campos de prosa, 0 sob invariante**.
2. **4 de 11 riscos citam a seção errada:** dois riscos de **proteção** citam a seção de
   imóveis (existe seção de seguros dedicada), o de **sucessão** cita a seção de renda do
   IRPF (existe seção de riscos e sucessão), e o de rentabilidade cita a de carga
   tributária. **REFUTADO** na mesma medição: a alegação de "âncora morta" — as **27
   citações resolvem, 27 de 27**. O link funciona; o destino é que está errado.
3. **O prompt se contradiz sobre `tools`:** a linha 441 do YAML convida o modelo a chamar
   `get_e5_section`; a **179 do mesmo arquivo** afirma que ele não tem ferramentas. O
   convite morto é **injetado no corpo sob budget** e é a causa proximal dos 3
   `campos_faltantes`.

## Por que os três juntos

O eixo é o mesmo: **o que o modelo escreve não é confrontado com o que a máquina sabe**.
Percentual fora do invariante, seção escolhida por prosa em vez de mapa declarado, e
ferramenta prometida sem existir são três formas de a autoria do modelo passar sem gate.

## Medição que fecha o mecanismo de (2)

Ler como o campo de seção do risco é atribuído no manifest. Se vem do LLM em vez de um mapa
declarado, é a classe *"nome vindo da prosa, não do produtor"*.

## Critério de aceite

1. Percentual em prosa entra no invariante monetário (ou a exclusão é decidida por ADR com
   o custo escrito — hoje ela está num comentário).
2. `section_id` do risco vem de **mapa declarado** por tema, não da prosa.
3. O convite a `tools` sai do prompt **ou** as ferramentas passam a existir; as duas linhas
   do YAML não podem discordar.
4. Gate de coerência: dois valores para a mesma grandeza na mesma seção reprova.

## Medição de abertura (2026-09-01) — o enunciado procede em 3 de 3, e erra em 2 de 4 critérios

Payload real do run `40d1af2a` (o mesmo da **U5**), decifrado do DB de dogfood. Nenhum
valor monetário reproduzido; só percentuais, nomes de campo e contagens.

### O que CONFIRMA

| Afirmação do enunciado | Medido | Veredito |
|---|---|---|
| dois valores para renda fixa na S1, **4,15 pp** | prosa **90,25%** (3×: `descricao`, `evidencia`, `impacto_qualitativo`) vs carimbo `alocacao_renda_fixa.valor_atual` = **94,4%** | ✅ exato |
| **27 percentuais** de prosa, **0** sob invariante | 27 tokens em 19 campos; `parecer_prose_money.py:16` é ancorado em `R$` por construção | ✅ |
| as **27 citações resolvem, 27 de 27** (refutação da "âncora morta") | reconfirmado | ✅ |
| o modelo **não tem** `tools` | `LLMService.call` (`pipeline/llm/litellm_client.py:133`) não tem parâmetro `tools`; as 19 entradas de `_meta.tool_trace` são **todas** `get_e5_jsonpath` pós-LLM | ✅ |

### O que o enunciado erra

1. **`campos_faltantes` são 8, não 3.** O **3** é o subconjunto atribuível: rodei a eviction
   real (cortou `plano_acao_atual`, `investimentos`, `independencia_financeira`) e
   **exatamente 3 dos 8** caem em seção evictada. Os outros 5 vêm de seções **mantidas** —
   4 deles são `$.endividamento.dividas[N].taxa_juros_aa`, o mesmo conceito 4×.
2. **A linha 441 é o convite MENOS importante — e é o único que NÃO está sob budget.**
   Hints são anexados **depois** do cap (`parecer_distiller.py:484-492`). O convite que
   está mesmo no corpo orçado é outro: `_eviction_marker` (`parecer_distiller.py:273`)
   injeta `" Recupere os dados via get_e5_section: {keys}."`. São **5** superfícies
   model-facing prometendo ferramenta, e as duas maiores o enunciado não nomeia: a regra
   **§3 "Tool use (drill-down)"** inteira do system prompt
   (`pipeline/llm/prompts/parecer_planejador.py:49-63`) e o heading literal
   **`## Tools disponíveis`** do user prompt (`:228-232`).
3. **Critério 1 é inerte como escrito.** "Percentual entra no invariante monetário" não
   pega o spread: `number_in_prose` é **telemetria**, não invariante ([[ADR-304]] §Emenda
   2026-08-03), e `MoneyToken.cents` é resíduo **sem consumidor** — não existe comparador
   prosa ↔ âncora em lugar nenhum do repo. Entrar nesse conjunto só incrementaria um
   contador de presença. O que pega o defeito é o critério 4.
4. **Critério 2 está REFUTADO.** `tema_canonico → section_id` **não é função** no output
   real: `Custo tributário` → {`S_IRPF_OTIMIZACAO`, `S_IRPF_RENDA`} e `Diagnóstico de
   dados` → {`S2`, `S_IRPF_RENDA`}, e nos dois casos **os dois destinos são legítimos**.
   Mapa por tema forçaria um e rotularia errado o outro.

### O mecanismo real do sintoma 2 — vocabulário sem produtor

Não é "nome vindo da prosa" genérico. É drift de contrato, medido:

- O manifest projeta {`S1`,`S2`,`S3`,`S7`,`S8`,`S9`,`S10`,`plano_de_acao`}.
- O enum `SectionId` (`pipeline/llm/schemas/parecer_planejador.py:49`, cópia à mão,
  duplicada em `backend/app/schemas/dto/planner_review/response.py:29`) oferece **4 a
  mais**: `S4`, `S_IRPF_RENDA`, `S_IRPF_OTIMIZACAO`, `S_parecer` — seções que o exec
  context **nunca popula**.
- Uso real: **13 de 33 itens (39%)** citam uma dessas 4, incluindo **5 de 11 riscos**.
- `dev/check_planner_manifest_coverage.py` **já avisa** exatamente sobre
  `S4`/`S_IRPF_RENDA`/`S_IRPF_OTIMIZACAO`/`S_PROTECAO` — é WARNING, sai `exit 0`, e não
  está conectado ao enum.
- `S9` ("Riscos e Sucessão — Lacunas de Proteção") foi **mantida** no contexto e recebeu
  **0 de 11** riscos; os 2 de proteção foram para `S4`.
- `S_PROTECAO` está fora do vocabulário **por decisão** (`pipeline/domain/types/suggestion.py:74`):
  sem renderer de callout, ampliar o enum criaria *emissor sem leitor* — a classe que a
  [[A40.l88]] fechou.
- No mesmo arquivo do enum, o irmão `MetricaKey` é **derivado** do catálogo, com o
  comentário "enum copiado envelhece calado". O `SectionId` é a exceção não declarada.

**Tensão que ninguém declarou:** `section_id` significa *proveniência* (de onde veio o
dado) ou *navegação* (o que o leitor deve abrir)? O teste
`TestSectionIdVocabulary::test_vocabulario_do_dominio_nao_deriva_do_layout` ancora o
vocabulário no **layout** (navegação); o dado disponível ancora no **manifest**
(proveniência). Hoje o modelo escolhe livre e o output mistura as duas leituras. Derivar
da âncora é viável (**25 de 26** raízes E5 → exatamente 1 seção; só `investimentos` é
ambígua {`S1`,`S3`}), mas só faz sentido sob a leitura de proveniência.

> Há folga para consertar por projeção em vez de por corte: a eviction ocorreu com
> **42,9% do orçamento de tokens ocioso** (`PV13-17` da mesma rodada), cap 16.384 bytes.
