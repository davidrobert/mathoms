---
id: A11.w6
type: lane
title: "Tech debt cleanup (6 tasks)"
sprint: A11
plan: PLAN-platform-review
status: open
aliases: ["A11.W6"]
depends_on: []
parallel_with: []
tags:
  - type/lane
  - sprint/a11
  - status/open
---


# A11.w6 — Tech debt cleanup (6 tasks)

> Migrada de tabela em `## Sprint A11` do BACKLOG (F4.A.followup, ADR-182).

## Contexto da tabela original

- **Onda:** 6 (12d)
- **Depende de:** W3 (T02 → W6-T02)
- **Plano:** [PLAN §W6](../../../plan/PLATFORM_REVIEW/_README.md#wave-6--tech-debt-cleanup-sprint-5-12-dias-dev)

## Status

**6/7 done · resta só W6-T01 residual** (reconciliado 2026-07-08 — fonte por
task: [PLAN Index](../../../plan/PLATFORM_REVIEW/_README.md#index)):

- W6-T01 (schema hardening) ◐ parcial — flip strict via A24.l7 ([[ADR-284]]); **resta**: split E4 em 7 sub-schemas + ADR-090 wire compliance (wire flip exige ADR `Proposto` antes) — único pickup real da wave
- W6-T02 (MLOps universal hooks) ✅ 2026-07-06 — [[ADR-307]] `Decidido` ([#796](https://github.com/davidrobert/mathoms/pull/796)+[#797](https://github.com/davidrobert/mathoms/pull/797))
- W6-T03 (F9.4/F9.5/F9.6 stage rename) ✅ 2026-07-06
- W6-T04 (doc hygiene) ✅ ([#111](https://github.com/davidrobert/mathoms/pull/111))
- W6-T05 (artifacts retention) ✅ pós-A11 — A32.l5 tombstone [[ADR-311]] + A33.l6 ([#844](https://github.com/davidrobert/mathoms/pull/844)); residual fora da task: flip `prune_mode=delete`
- W6-T06 (ADR-150 decisão) ✅ ([#110](https://github.com/davidrobert/mathoms/pull/110); [[ADR-150]] `Decidido` 2026-07-03)
- W6-T07 (`services/` taxonomy) ✅ pós-A11 — A33.l9 ([#855](https://github.com/davidrobert/mathoms/pull/855)); [[ADR-285]] `Decidido`
