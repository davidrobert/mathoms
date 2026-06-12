---
id: ADR-291
type: adr
title: "from_stage lê stages run-scoped upstream de um base_run pinado (fallback ADR-291)"
status: Proposto
phase: "A25 · dogfood"
date: "2026-06-12"
relates_to:
  - "[[ADR-132]]"
  - "[[ADR-241]]"
  - "[[ADR-278]]"
  - "[[ADR-080]]"
supersedes: []
superseded_by: []
aliases: ["ADR 291", "base_run fallback", "from_stage base run"]
tags:
  - type/adr
  - status/proposto
  - area/pipeline
  - area/persistence
---

# ADR-291 — `from_stage` lê stages run-scoped upstream de um `base_run` pinado

**Status:** Proposto (A25 · dogfood) • **Data:** 2026-06-12 • **Relaciona**
[[ADR-132]] (lifecycle scoping), [[ADR-241]] (E2 workspace-scoped),
[[ADR-278]] (data lineage), [[ADR-080]] (incremental).

> **Não reabre [[ADR-241]].** E3/E4/E5 continuam run-scoped (invariantes
> cross-account: dedup, saldo continuity, fatura sintetizada ADR-097 D2).
> O que muda: run com `from_stage` ganha um **run base de referência
> coerente** para os stages upstream que ele não reagenda — fallback
> **pinado em um run único**, não latest-per-key.

## Contexto

Bug descoberto no dogfood A25.l2 (2026-06-12): `POST /pipeline/run` com
`from_stage="E4"` produz E4/E5 **vazios** (`despesas.total_transacoes=0`)
e o run completa "com sucesso" — o relatório do usuário zera
silenciosamente e um `Report` novo é criado sem nenhum sinal de erro.

Causa raiz: `from_stage` cria um `PipelineRun` **novo**;
`DBArtifactStore.read` filtra por `pipeline_run_id` atual e o fallback
workspace-wide (`_WORKSPACE_SCOPED_STAGES`, ADR-132/241) não cobre
E3/E4/E5. Como `list_keys` é workspace-wide e `read` é run-scoped, o
`E4CategorizerAdapter` enxerga as keys de E3 mas lê `None` para todas —
itera nada, e os `or {}` defaults espalhados propagam o zero até o
relatório. `from_stage="E5"` sofre o mesmo (E5 lê E4 **e** E3);
`"E5.N"`/`"E7"` idem (leem E5). `"E3"` funciona por acidente — E2 é
workspace-scoped desde ADR-241.

## Decisão

1. **Fallback pinado em base_run no store.** `DBArtifactStore` ganha
   `base_run_id` + `base_run_fallback_stages` opcionais; `read()` cai em
   match **exato** `(base_run_id, stage, key)` apenas para stages nesse
   set (`_get_in_base_run`, separado de `_get_latest_in_workspace` —
   mecânicas com invariantes distintos). Telemetria
   `mathoms.pipeline.artifact.base_run_fallback` (espelha ADR-241).
2. **Resolver no trigger + fail-fast.** `trigger_pipeline` calcula os
   artifact stages run-scoped que o run lê mas não produz
   (`pipeline.stage_spec.run_scoped_upstream_reads`: E4→{E3},
   E5→{E3,E4}, E5.N/E7→{E5}) e escolhe `base_run` = run mais recente do
   workspace com rows em `pipeline_artifacts` para **todos** eles
   (superset). Critério é presença de rows — sessão por-stage só comita
   em sucesso — não `pipeline_runs.status`. Sem candidato → **422**
   ("execute o pipeline completo primeiro") em vez de relatório zerado.
3. **Pin único, nunca per-stage.** Resolução por-stage poderia casar E4
   do run Y com E3 do run X — universos distintos, exatamente o bug
   cross-account que ADR-241 alt-(a) rejeitou. O pin garante que
   E3↔E4↔E5 lidos coexistiram num run internamente consistente.
4. **Coluna `pipeline_runs.base_run_id`** (nullable, FK `ON DELETE SET
   NULL`) registra qual run foi escolhido — lineage consultável,
   complemento de `pipeline_artifacts.data_source_id` (ADR-278). NULL =
   run full/incremental/resume.
5. **Defesa em profundidade no adapter.**
   `E4CategorizerAdapter.load_reconciled_accounts` levanta
   `RuntimeError` quando `list_keys("E3")` retorna keys mas **zero**
   payloads são legíveis — nunca mais completa com 0 silencioso, mesmo
   se um fallback futuro regredir.

## Alternativas rejeitadas

- **(a) Promover E3/E4/E5 a `_WORKSPACE_SCOPED_STAGES`.** Já rejeitada
  em ADR-241: latest-per-key cross-run quebra invariantes cross-account
  e ressuscitaria keys de contas removidas em runs full ("conta
  fantasma").
- **(b) Copy-forward de artefatos para o run novo.** Rejeitada em
  ADR-132 e ADR-241 pelo custo de duplicação de payload; o fallback de
  leitura resolve sem duplicar.
- **(c) Bloquear `from_stage` sempre.** Mataria a feature (reprocessar
  E4/E5 após ajuste de categorização é fluxo legítimo). O 422 só ocorre
  quando não há base coerente.

## Consequências

- ✅ `from_stage="E4"/"E5"/"E5.N"/"E7"` voltam a produzir relatório
  correto, reusando o último run coerente.
- ✅ Classe "relatório zerado silencioso" eliminada (guard no adapter +
  422 no trigger).
- ✅ Runs full/incremental/resume **inalterados** (defaults
  None/frozenset(); `resume_pipeline_run` reusa o mesmo `run_id` e não
  ativa fallback).
- ⚠️ **`from_stage` encadeado não compõe**: run2=`from_E4` não grava E3;
  um run3=`from_E5` exige base com E3+E4 e escolherá o último run
  *completo o suficiente* (possivelmente ignorando o E4 mais novo de
  run2). Staleness aceita, auditável via `base_run_id`.
- ⚠️ GC futuro de `pipeline_artifacts` (débito ADR-241 §Follow-up 1) não
  pode assumir que artefatos de runs antigos são inalcançáveis: um run
  `from_stage` pode referenciá-los. FK `SET NULL` evita travar o GC;
  política de retenção deve considerar `base_run_id`.

## Gates de regressão

- Unit store: fallback exato pinado; stage fora do set **não** cai em
  fallback (protege contra conta fantasma em stage recomputado).
- Unit trigger: 422 sem run qualificado; escolha do run mais recente com
  superset; `base_run_id` gravado.
- Unit adapter: keys visíveis + zero legíveis → raise; `list_keys` vazio
  → E4 vazio legítimo (sem raise).
- Integração: full run → `from_stage="E4"` reusa E3 do base com
  transações > 0.
