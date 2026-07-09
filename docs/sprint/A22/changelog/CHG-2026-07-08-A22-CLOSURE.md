---
id: CHG-2026-07-08-A22-CLOSURE
type: changelog-entry
date: "2026-07-08"
sprint: A22
lane: "[[A22.l4]]"
adrs: ["[[ADR-300]]", "[[ADR-301]]"]
prs: [801]
summary: |
  Fechamento da Sprint A22 (Launch Trust F3 — Parecer defensável) como `done`,
  retroativo após reconciliação contra o código provar as 5 lanes em `main`.

  Registra também a `l4` (F3-O4, drift detection), que shipou em #801 sem CHG:
  `backend/app/services/parecer_drift_monitor.py` + hook fail-open pós-commit em
  `planner_review_persistence._safe_persist`. **5 sinais** (3 da lane + 2 do
  co-design prompt-engineer): confidence Δ e needs_review Δ com banda
  `max(floor, 2·SE)` e piso N=8; tokens/custo Δ ±30%; duration p95 Δ ±40% (proxy
  de reask storm ADR-292/294); model swap sob mesma prompt_version (warn N=1).
  Pin de model travado por `tests/unit/pipeline/test_parecer_model_pin.py`.

  Verificação de fechamento (2026-07-08): 337 testes Python + 5 React verdes —
  7 red lines determinísticas (RL1–RL7), 24 fixtures holdout estratificadas,
  `additionalProperties:false` no schema do parecer, fallback atômico
  backend (`test_llm_failure_returns_needs_review`) + React (`SParecerSection`),
  20 invariantes INV-D de dedup de dívida (schema formal com
  `additionalProperties:false` em `baseline_patrimonial.schema.json`), drift
  5 sinais + model pin. KR-a..KR-e todos batidos. Prompt-side das red lines
  (REGRA 14 + `PROMPT_VERSION 2.1.0`) entregue em #700/#701.

  Residual owner-gated (fora do escopo da janela, não bloqueou o fechamento):
  KR5 deploy reproduzível (GHCR/Coolify, ADR-228 G3), KR4 off-site R2 (ADR-228
  G2), LLM-real nightly como gate (budget de provider), F1-O5 dedup de veículo
  cross-year (Defer P2).
tags:
  - type/changelog-entry
  - sprint/a22
  - area/llm
---
