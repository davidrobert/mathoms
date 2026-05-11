---
id: CHG-2026-05-11-FEAT-CAT-LEARNING-LOOP-FRONTEND
type: changelog-entry
date: "2026-05-11"
sprint: A12
lane: "[[A12.cat-learning-loop]]"
prs: [199, 200, 201, 202, 203]
commits: ["6649ce7", "e754791", "6a682c3", "db3002e", "ff7fbf2"]
summary: |
  feat(frontend): P4 learning loop UI mínima (toast + modal + badge) +
  gate técnico dogfood (smoke E2E 11/11 PASS) + housekeeping +
  purge script single-tenant pré-produção. A12.cat-learning-loop pronto
  para gate dogfood humano.
tags:
  - type/changelog-entry
  - sprint/a12
  - area/frontend
  - area/categorization
  - area/dev
---

# feat(frontend): P4 UI mínima + gate técnico dogfood (A12)

Bloco de 5 PRs entregue 2026-05-11 que destrava o gate dogfood humano:
housekeeping + handoff PM + purge script + gate técnico + P4 UI mínima.

**Entregue:**

- **PR #199** (`6649ce7`) — Housekeeping pós-P3: lane in_progress
  marcada com P1-P3 ✅, gate dogfood explicitado como próximo passo.
- **PR #200** (`e754791`) — Handoff dogfood: PM checklist em
  `docs/reference/RUNBOOK.md §9` + critérios objetivos (≥5 regras,
  revert_rate ≤30%, ≥3 regras com ≥3 matches retroativos em 7d
  wall-clock).
- **PR #201** (`6a682c3`) — `scripts/purge_test_workspaces.py`
  (single-tenant cleanup pré-produção) — remove workspaces de teste
  preservando único workspace canônico do CEO.
- **PR #202** (`db3002e`) — `scripts/dogfood_gate_a12.py` + internals em
  `dev/_dogfood_gate_a12/` (10 módulos ≤200 linhas). SQLite isolado em
  `_scratch/`, fixture realista determinística (~2880 txs / 24m / seed
  fixo). Bateria de 5 regras (IFOOD, MERCADOLIVRE, UBER, PIX, "13") +
  simulação de revert ~20%. **11 invariantes técnicas avaliadas →
  verdict PASS 11/11** (sticky manual ✓, mês fechado ✓, internal
  transfer blacklist ✓, keyword warnings ✓, applied_count alignment ✓,
  soft/hard cap ✓). Idempotente, ~10s.
- **PR #203** (`ff7fbf2`) — P4 frontend **UI mínima single-tenant**:
  - Toast pós-override com CTA "Criar regra" (dispensável).
  - Modal `CreateRuleDialog`: keyword + target pré-preenchidos, preview
    com contadores (total, em meses fechados, com override manual,
    valor total BRL), warning amarelo + checkbox quando
    `requires_user_confirmation`, sync (≤500 matches) ou 202 async +
    polling de `/apply-status` a cada 5s.
  - Badge "Regra" (sparkle icon) em transações `override_source='rule'`.
  - Heatmap mês fechado: matches em meses publicados destacados com
    lock icon + `var(--semantic-warning)` (ressalva financial-planner
    sobre ADR-187).
  - Feature flag `learning_loop_enabled` per-workspace via hook
    `useFeatureFlags`. Kill switch:
    `feature_flags_service.set_flag(ws, "learning_loop_enabled", False)`.
  - Backend touch: `TransactionItem.override_source` + propagação em
    `apply_overrides` + filtro `deleted_at IS NULL` em
    `load_overrides_map` (paridade ADR-188 §D1).

**Cortado vs plano canônico** (V2 pós-tração):

- Side-panel 480px (substituído por modal simples).
- Highlight-to-extract de keyword (digitação manual no MVP).
- Sub-tab "Regras promovidas" em `/config → Categorias` (V2.A).

**Próximo passo:** gate dogfood humano (CEO 7d wall-clock no `5@5.com`).
Kill switch via feature flag suficiente para single-tenant pré-produção.
