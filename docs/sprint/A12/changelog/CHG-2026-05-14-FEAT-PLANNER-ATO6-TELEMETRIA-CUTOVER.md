---
id: CHG-2026-05-14-FEAT-PLANNER-ATO6-TELEMETRIA-CUTOVER
type: changelog-entry
date: "2026-05-14"
sprint: A12
lane: "[[A12.planner-review-ato6]]"
prs: []
commits: []
summary: |
  feat(planner): Ato 6 (último) — telemetria M4 + cross-provider weekly +
  deprecation do review_finances + healthcheck órfão. Fecha PLANNER_REVIEW.
breaking: false
tags:
  - type/changelog-entry
  - sprint/a12
  - area/llm
  - area/pipeline
  - area/observability
adrs:
  - "[[ADR-128]]"
  - "[[ADR-199]]"
  - "[[ADR-206]]"
---

# feat(planner): Ato 6 — telemetria + cutover + hardening

Ato 6 (último) do plano [`PLANNER_REVIEW`](../../../archive/PLANNER_REVIEW-2026-07-09.md).
Hardening operacional pós-shipping — não bloqueia uso, fecha lacunas
de evolução de longo prazo da feature parecer planejador.

**T-23 — Telemetria de campo faltante ([[ADR-206]]):**

- Tabela `planner_field_requests` (migration `f4e5d6c7b8a9`) — PK UUID +
  FK workspace + FK planner_review + `field_path` (JSONPath, sem valor
  cliente) + `motivo` + `reason` + `created_at`. UNIQUE
  `(planner_review_id, field_path)` para idempotência intra-batch.
- Model `backend/app/models/planner_field_request.py`.
- Repository `PlannerFieldRequestRepository.top_requested_fields(days,
  limit)` — agrega por path com freq + workspaces_count desc.
- Persistência integrada em `planner_review_persistence._do_persist` —
  bulk-insert lê `content_json.campos_faltantes_pediria_se_iterasse[]`
  do parecer com dedup intra-batch.
- Endpoint admin `GET /admin/planner-review/field-requests/top` (gated
  por `require_internal_operator`) — input para review semanal do
  `product-manager` sobre evolução do manifest v2.

**T-24 — Cross-provider weekly smoke:**

- Workflow `.github/workflows/llm-cross-provider-smoke.yml` — cron
  segunda 06:00 UTC + `workflow_dispatch`. Matrix providers
  `[anthropic, openai]`. Skipa se secret ausente (não bloqueia CI normal).
- Marker `@pytest.mark.cross_provider` em testes do golden — assertions
  estruturais (schema, hard caps, anti-ticker, dedup_key reproduzível),
  não textuais. Cap de custo `< $0.50` por chamada.
- Falha → cria Issue `cross-provider-drift` automaticamente.

**T-25 — Deprecate `review_finances` ([[ADR-128]] superseded by [[ADR-199]]):**

- `pipeline/stages/review_finances.py` emite `DeprecationWarning` ao
  executar + log estruturado.
- `StageSpec.is_deprecated: bool = False` adicionado; `review_finances`
  marcado `is_deprecated=True` no `STAGE_REGISTRY`.
- [[ADR-128]] frontmatter `phase` atualizado para "A6-cleanup (superseded
  em A12.X — deprecation Ato 6)". Sprint A12.X remove código + decide
  política de retenção de artifacts antigos.

**T-26 (bônus) — Healthcheck artifact órfão:**

- CLI `backend/scripts/check_orphan_planner_artifacts.py` — query
  artifacts E6-parecer sem `PlannerReview` correspondente > 1h. Log
  estruturado + count. Flag `--fix` retroativa cria metadata (idempotente).

**T-27 (bônus) — Golden mensal com LLM real:**

- Workflow `.github/workflows/planner-golden-monthly.yml` — 1° dia do
  mês 06:00 UTC. Compara output vs baseline em
  `tests/golden_baselines/parecer_monthly_<YYYY-MM>.json`. Marker
  `@pytest.mark.monthly_real`.

Feature parecer planejador **100% completa** após este Ato:

- Atos 0–5: stage runtime + UI + tier filter
- Ato 6: telemetria M4 + cross-provider monitoring + cutover legado +
  healthcheck + golden mensal real
