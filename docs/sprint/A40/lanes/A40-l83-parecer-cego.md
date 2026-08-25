---
id: A40.l83
type: lane
title: "Parecer cego em três eixos: não recebe a incerteza, não consegue citar o que recebe, e o guardrail que deveria pegar isso inverte o diagnóstico"
sprint: A40
plan: PLAN-deterministic-authority
status: open
priority: P0
branch_slug: a40-l83-parecer-cego
adrs:
  - "[[ADR-200]]"
  - "[[ADR-206]]"
  - "[[ADR-304]]"
depends_on: []
tags:
  - type/lane
  - sprint/a40
  - status/open
  - priority/p0
  - area/pipeline
  - area/llm
  - area/report
---

# A40.l83 — Parecer cego (RV8-05 · RV8-07 · RV8-16)

> **O parecer é a única superfície que PRESCREVE.** Tudo o mais no relatório
> descreve; ele recomenda. Os três achados desta lane são independentes no
> código e convergem no mesmo efeito: ele prescreve sem ver, sem poder citar, e
> sem que o instrumento de eval registre nenhuma das duas coisas.

## O que foi medido no r8 (run `d0f6260a`)

**RV8-05 — não recebe a incerteza.** `config/prompts/parecer_planejador.yaml` é
**whitelist**: o que não está declarado não entra. Grep dos seis campos de
incerteza construídos na A40 devolve **zero** ocorrências —
`investimentos_nao_atribuidos`, `cobertura_investimentos`, `nao_classificado_pct`,
`diagnostico_confianca`, `guarda_de_sinal`, `pl_ressalva`. O `_meta.tool_trace`
do run confirma que o pull discricionário não compensa: **6 iterações, 3 paths
únicos, todos em `reserva_emergencia`**.

**O modelo não alucinou — e isso muda o remédio.** Ele ressalvou **3 de 3**
lacunas que o payload declarou e **0 de 1** da que o payload não declarou. O
defeito é de projeção, não de prompt. Consertar o prompt seria consertar o lado
errado.

**RV8-07 — não consegue citar.** `measure_anchorability` sobre o E5 **real**
deste run devolve `ancoraveis: []` — **0 de 36** caminhos monetários visíveis têm
rota de citação, com `catalogo_renderizado: 16` de `catalogo_construido: 30`. O
snapshot que **gateia** (`dev/snapshots/parecer_ancorabilidade.json`, corpus
sintético `make_workspace_e5`) reporta **11/28 = 39,3%**.

Mecanismo: `_PRIORITY_ROOTS` (`parecer_citation_catalog.py:67`) ranqueia
(`:205-207`), `max_entries=30` corta (`:232,242`) e `select_catalog_entries(...,
max_bytes)` (`:268`) trunca. O renderizado colapsa em **2 raízes**
(`reserva_emergencia` + `endividamento`), cuja cardinalidade **escala com o
cliente**: quem tem mais dívidas nunca vê investimentos.

**RV8-07b — o eval é fail-open.** `coverage_failed`
(`parecer_evidencia.py:192-194`) devolve `failures_by_layer.get(_COVERAGE_LAYER)`
— conta só `missing_path`, que **só existe para âncora emitida**. Item com
`ancoras: []` não gera entry. Resultado no r8: `coverage_failed: 0` com **17 de
21 itens sem âncora nenhuma**. Pior: `itens_sem_ancora` **existe** como campo
(`:178`, incrementado em `:292`) e **não entra** em `log_evidencia_kpi`
(`:252-262`), que loga apenas `verified`/`coverage_failed`/`correctness_failed`.
O painel lê 100% de cobertura, zero falhas.

**RV8-16 — o guardrail inverte o diagnóstico.** `_meta.field_request_audit` traz
2 pedidos marcados `field_request_spurious`, **ambos legítimos**, ambos removidos
do output do usuário:

1. Path cortado do catálogo por `max_bytes`. `_classify_campo`
   (`parecer_pos_llm_guardrails.py:266`) pergunta `classify_field_path(e5_data,
   path)` — **consulta o E5**, enquanto a afirmação do modelo era sobre o
   **catálogo**. Predicado e afirmação falam de universos diferentes.
2. Valor `'desconhecida'` no E5. `_ABSENCE_SENTINELS = {"", "N/D", "nan"}`
   (`:62`) não o contém ⇒ `present` ⇒ spurious.

Taxa de falso-positivo: **2 de 2**. E o contador que deveria sinalizar
**truncamento de contexto** é lido como "modelo alucinou path".

## Armadilhas

**A pior: rebaselinar o snapshot pelo mesmo corpus re-certifica a cegueira.**
O gate é verde porque o corpus sintético não parece com produção — cardinalidade
de dívidas e baldes de reserva muito menor. Rebaseline tem de vir de corpus com
cardinalidade comparável à real, senão o instrumento continua medindo outra coisa
e o próximo run reabre o achado. Classe conhecida: fixture que clampa o que
produção não clampa.

**Subir `max_bytes` sozinho não resolve, e round-robin também não.** A medição do
r8 indica: semear pelo **conjunto visível** (`iter_visible_money_paths`) antes de
completar com o walk genérico é o que move a agulha; round-robin por raiz sem
mudar o seed chega a ~5,6%. Re-meça antes de escolher — o corpus muda.

**Mexer no manifest muda o parecer.** Golden precisa de rebaseline consciente e
`PROMPT_VERSION` precisa de bump (há hook `check_prompt_version_bumped`).

**`out_of_catalog` é mudança de contrato.** O enum de `reason` vive sob
`additionalProperties: false` ([[ADR-206]]) — schema + bump, não só código.

**A camada de token monetário em prosa é decisão vigente, não descuido.**
`money_tokens_total` está fora de `_HARD_LAYERS` por [[ADR-304]] §Emenda
2026-08-03. Se a lane quiser mudar isso, é emenda datada — não edite em silêncio.

## Escopo

| Peça | Superfície | Natureza |
|---|---|---|
| RV8-05 | `config/prompts/parecer_planejador.yaml` (bloco `patrimonio`) | projeção declarativa + `narrative_hint` de supressão |
| RV8-05b | `dev/_planner_coverage_internals.py:325-335` | drift E5↔manifest é `warn` e 3 ADRs passaram por ele — promover a `fail` com lista de escape versionada |
| RV8-07 | `parecer_citation_catalog.py` (`_PRIORITY_ROOTS`, `select_catalog_entries`) | semear pelo conjunto visível |
| RV8-07b | `parecer_evidencia.py` (`log_evidencia_kpi`) | `itens_sem_ancora` vira KPI logado **e** gate do golden mensal |
| RV8-16 | `parecer_pos_llm_guardrails.py` (`_classify_campo`, `_ABSENCE_SENTINELS`) | novo reason + placeholder de domínio como `empty` |

## Critério de aceite

**Corretude** — `measure_anchorability` sobre o **E5 real** (não o sintético)
≥ 80%. Rodável in-process, custo zero: é assim que o número desta lane foi obtido.

**Completude** — os seis campos de incerteza projetados, e o gate de drift
E5↔manifest reprovando quando o schema ganha campo de incerteza que o manifest
ignora. `field_requests_spurious` volta a **0** neste payload, com os dois pedidos
reaparecendo no output.

**Consistência** — o predicado que classifica pedido de campo consulta o **mesmo
universo** sobre o qual o modelo se pronunciou (catálogo, não E5). Duas perguntas
diferentes, dois reasons diferentes.

**Precisão** — o KPI publicado distingue *"a âncora resolve?"* de *"houve
âncora?"*. `coverage_failed` fica como está; a densidade
(`itens_sem_ancora / itens_total`) entra ao lado. Um número que só pode dar zero
não é medida.

**Prova de fecho (predicado do r9)** — parecer com ≥1 ressalva em item de tema
`Alocação`; ancorabilidade sobre E5 real acima do piso; e `itens_sem_ancora`
presente na telemetria com valor não-trivial ou zero **explicado**.

## Delegação

Co-design `prompt-engineer` (projeção, catálogo, eval) + `financial-planner`
(que ressalva o parecer deve emitir quando a fatia sem dono cruza o piso —
é regra de domínio, não de prompt). `senior-cto` decide se o drift
E5↔manifest vira `fail` bloqueante.

## Rastro

RV8-05, RV8-07 e RV8-16 do §r8 de [[PIPELINE-REVIEWS-active]] (run `d0f6260a`,
2026-08-24). Medições refeitas nesta lane. Cru off-git em
`storage/<uuid>/reviews/20260824-2235-d0f6260a/`.
