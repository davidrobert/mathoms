---
id: A11.w4
type: lane
title: "Production readiness (5 tasks)"
sprint: A11
plan: PLAN-platform-review
status: blocked
aliases: ["A11.W4"]
depends_on: []
parallel_with: []
tags:
  - type/lane
  - sprint/a11
  - status/blocked
---


# A11.w4 — Production readiness (5 tasks)

> Migrada de tabela em `## Sprint A11` do BACKLOG (F4.A.followup, ADR-182).

## Contexto da tabela original

- **Onda:** 4 (10d)
- **Depende de:** W3 ✅ + drill backup
- **Plano:** [PLAN §W4](../../../plan/PLATFORM_REVIEW/_README.md#wave-4--production-readiness-sprint-3-10-dias-dev)

## Status

**1 done · 2 parciais · 2 blocked** (reconciliado 2026-07-08 — fonte por task:
[PLAN Index](../../../plan/PLATFORM_REVIEW/_README.md#index)):

- W4-T01 (off-site backup R2 + drill) ◐ parcial — drill dump→restore em CI ✅ (A21.l9, [#538](https://github.com/davidrobert/mathoms/pull/538)); off-site R2 **owner-gated** (bucket/keys; [[ADR-174]] segue `Proposto`; gates G2/G3 [[ADR-228]])
- W4-T02 (Coolify webhook + SHA-pinned) ◐ parcial — SHA pinning ✅ (A20.L2, [#510](https://github.com/davidrobert/mathoms/pull/510)); webhook GHCR/Coolify = A20 L4, **owner-gated** (token)
- W4-T03 (Sentry SaaS EU) ☐ blocked — **owner-gated** (signup região EU + DSN)
- W4-T04 (rate limit LLM/upload/pipeline) ✅ 2026-07-02 ([#720](https://github.com/davidrobert/mathoms/pull/720))
- W4-T05 (status page + alertas + drill) ☐ blocked — dep W4-T03 + **owner-gated** (signups Instatus/UptimeRobot) + prod pública

Gates operacionais G1–G5 são rastreados por [[ADR-228]] (prazo 7d pós-cutover
`app.mathoms.ai`) e não bloqueiam closure code-complete.
