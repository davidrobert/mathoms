---
id: CHG-2026-05-11-FEAT-CAT-LEARNING-LOOP-BACKEND
type: changelog-entry
date: "2026-05-11"
sprint: A12
lane: "[[A12.cat-learning-loop]]"
adrs:
  - "[[ADR-188]]"
prs: [195, 196, 197, 198]
commits: ["7f5fe96", "996ced6", "8faac98", "d660daf"]
summary: |
  feat(api): backend API completo do learning loop — preview, commit,
  revert, telemetria mínima, async Celery + perf hardening. A12.P3
  (ADR-188 Decidida).
tags:
  - type/changelog-entry
  - sprint/a12
  - area/api
  - area/categorization
  - area/db
---

# feat(api): backend completo do learning loop (A12.P3)

P3 do plano CAT_LEARNING_LOOP entregue em 4 PRs sequenciais.
[[ADR-188]] **Decidida** (schema evolution + soft-delete + partial unique
+ revert_count split — consolida 7 ressalvas do gate triple P2 + R1-R8
data-engineer).

**Entregue:**

- **PR #195** (`7f5fe96`) — ADR-188 Proposto + track P3.
- **PR #196** (`996ced6`) — Schema delta: soft-delete (`deleted_at`),
  partial unique `(workspace_id, keyword) WHERE deleted_at IS NULL`,
  split `revert_count_manual_edit` vs `revert_count_rule_disabled` + ON
  CONFLICT safety net no apply.
- **PR #197** (`8faac98`) — Endpoints:
  - `POST /workspaces/{ws}/categorization/rules/preview` (não persiste).
  - `POST /workspaces/{ws}/categorization/rules` (cria + aplica).
  - `DELETE /.../rules/{id}` (soft-delete + remove overrides
    `source=rule`).
  - `GET /workspaces/{ws}/categorization/rules` (paginado com
    contadores).
  - `POST /.../rules/{id}/disable` (toggle enabled).
  - Telemetria mínima (4 contadores `mathoms.categorization.*`):
    `transactions_categorized_total{source}`, `rules_applied_total`,
    `rules_reverted_total`, `time_to_rule_seconds`.
  - Hard cap 200 regras / soft warning 50.
- **PR #198** (`d660daf`) — Async Celery `apply_rule_overrides_task`
  (>500 matches → 202 + polling de `/apply-status`), perf hardening, e
  reviewer ressalvas.
- Snapshot OpenAPI regenerado.

Pré-requisito P4 (Frontend) e gate dogfood.
