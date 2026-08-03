---
id: A40.l18
type: lane
title: "Criticidade de stage: add-on advisory não veta o entregável; partial_failure alcançável"
sprint: A40
plan: PLAN-report-trust
status: open
priority: P0
branch_slug: a40-l18-criticidade-de-stage
adrs:
  - "[[ADR-357]]"
depends_on:
  - "[[A40.l21]]"
tags:
  - type/lane
  - sprint/a40
  - status/open
  - priority/p0
  - area/pipeline
  - area/backend
---

# A40.l18 — `criticidade-de-stage`

> Onda 3 da A40 (§Frente 4 de [[PLAN-report-trust]]). Fecha a **classe**, não o caso.
> `depends_on` [[A40.l21]] por **ordem reader-first**: os leitores toleram
> `partial_failure` antes de o writer o emitir.

## Problema

`StageResult.success: bool` é o único canal e `False` significa
indistintamente "o pipeline não pode continuar" e "este add-on não entregou". A
classe tem **3 membros vivos** na cauda pós-`analyze_finances`:
`review_finances_holistic`, `generate_narratives` (`:966,975`) e `validate_cross`
(`:699,711,717`). Qualquer um destrói o entregável.

`PipelineRunStatus.partial_failure` existe desde a migration inicial e **nunca é
atribuído**. `_finalize_pipeline_outcome` faz `if not has_failure:
_run_post_processing(...)` — e o post-processing é quem cria `reports`,
materializa lineage edges e sincroniza status E2.

[[ADR-199]] já declara o parecer *"não-bloqueante"* em
[`pipeline/stage_spec.py:243`](../../../../pipeline/stage_spec.py). Esta lane faz
o código cumprir a política escrita.

## Decisão

Ver [[ADR-357]] (`Proposto` — abrir **antes** do PR de implementação). Resumo:
`criticality: required|degradable` no registry (default fail-closed);
`StageResult.outcome ∈ {completed, skipped, degraded, failed}` derivado de
`(retorno, criticality)` no orquestrador; `PipelineStageStatus.degraded` novo;
`partial_failure` escrito; `failed_at_stage` **não** populado em degradação;
`degraded` **entra em `_STAGE_DONE_STATUSES`** (senão o redelivery re-paga o
stage LLM); artifact degradado commitado, nunca publicado — **exceto**
`generate_narratives`, que escreve na chave do E5 e corromperia o deliverable;
`_finalize_run` 3-way e post-processing rodando em degradação.

## Critério de aceite

- Fake de stage `degradable` com `success: False` ⇒ run `partial_failure`,
  1 row em `reports` com FK para o artifact E5, `stage_log.status == degraded`,
  `run.failed_at_stage is None`.
- Mesmo fake em stage `required` ⇒ `failed`, zero row em `reports`
  (comportamento atual preservado).
- **Teste de injeção nos 3 membros vivos** assertando que o report existe (KR-2).
- Regressão de redelivery: run com stage degradado ⇒ zero chamada LLM nova.
- `generate_narratives` degradado **não** deixa o payload `analyze_finances`
  corrompido (comparação byte-a-byte com o pré-stage).
- Stage `degradable` com `validation.valid=False` ⇒ `degraded`, **não**
  `needs_review`; zero row em `StageReview`; `paused_at_stage is None`.
- Gate estático: todo stage após `analyze_finances` é `degradable`; todo stage
  até ele é `required`. Falha se alguém inserir stage no meio sem decidir.
- `make update-openapi-snapshot` ⇒ **diff vazio**. Diff ⇒ status novo foi
  adicionado e a [[ADR-357]] §3 foi violada.
- `dev/check_pipeline_boundaries.py` verde (mapeamento `outcome →
  PipelineStageStatus` mora em `backend/`).
- Log estruturado `stage_degraded` com `stage`, `criticality`, `reason_class`
  (nunca a prosa), `cost_usd`, `run_id`.
