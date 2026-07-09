---
id: A11.w6
type: lane
title: "Tech debt cleanup (6 tasks)"
sprint: A11
status: shipped
aliases: ["A11.W6"]
depends_on: []
parallel_with: []
tags:
  - type/lane
  - sprint/a11
  - status/shipped
---


# A11.w6 — Tech debt cleanup (6 tasks)

> Migrada de tabela em `## Sprint A11` do BACKLOG (F4.A.followup, ADR-182).

## Contexto da tabela original

- **Onda:** 6 (12d)
- **Depende de:** W3 (T02 → W6-T02)
- **Plano:** [PLAN §W6](../../../archive/PLATFORM_REVIEW_PLAN-2026-07-08.md#wave-6--tech-debt-cleanup-sprint-5-12-dias-dev)

## Status

**6/7 done · resta só W6-T01 residual** (reconciliado 2026-07-08 — fonte por
task: [PLAN Index](../../../archive/PLATFORM_REVIEW_PLAN-2026-07-08.md#index)):

- W6-T01 (schema hardening) ◐ parcial — flip strict via A24.l7 ([[ADR-284]]); **resta**: split E4 em 7 sub-schemas + ADR-090 wire compliance (wire flip exige ADR `Proposto` antes) — único pickup real da wave
- W6-T02 (MLOps universal hooks) ✅ 2026-07-06 — [[ADR-307]] `Decidido` ([#796](https://github.com/davidrobert/mathoms/pull/796)+[#797](https://github.com/davidrobert/mathoms/pull/797))
- W6-T03 (F9.4/F9.5/F9.6 stage rename) ✅ 2026-07-06
- W6-T04 (doc hygiene) ✅ ([#111](https://github.com/davidrobert/mathoms/pull/111))
- W6-T05 (artifacts retention) ✅ pós-A11 — A32.l5 tombstone [[ADR-311]] + A33.l6 ([#844](https://github.com/davidrobert/mathoms/pull/844)); residual fora da task: flip `prune_mode=delete`
- W6-T06 (ADR-150 decisão) ✅ ([#110](https://github.com/davidrobert/mathoms/pull/110); [[ADR-150]] `Decidido` 2026-07-03)
- W6-T07 (`services/` taxonomy) ✅ pós-A11 — A33.l9 ([#855](https://github.com/davidrobert/mathoms/pull/855)); [[ADR-285]] `Decidido`

## Fechamento (closure A11, 2026-07-08)

Lane fechada com a sprint (`done`) — 6/7 tasks entregues (2 delas
pós-A11, via A32.l5/A33.l6/A33.l9). O residual do W6-T01 (split E4 +
wire ADR-090) sai como **backlog candidate** (emenda [[ADR-228]];
track `docs/sprint/W6/tracks/w6t01-schema-hardening.md` preservado).
