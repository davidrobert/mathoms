---
id: A43.l6
type: lane
title: "Operação do canal: audit, rate limit, SLO, redaction e runbook"
sprint: A43
plan: PLAN-competitive-pierre
status: planned
priority: P1
branch_slug: a43-l6-operacao-audit-rate-limit-e-redaction
depends_on: ["[[A43.l4]]", "[[A43.l5]]"]
adrs: ["[[ADR-110]]", "[[ADR-111]]", "[[ADR-175]]", "[[ADR-275]]", "[[ADR-319]]"]
tags: [type/lane, sprint/a43, status/planned, priority/p1, area/observability, area/ops, area/security]
---

# A43.l6 — Audit, rate limit, SLO, redaction e runbook

> **Origem:** [[A43]] · [[PLAN-competitive-pierre]].

## Decisão

Instrumentar apenas envelope: actor, workspace, client/channel, tool, outcome,
error class, latency, bytes bucket e correlation id. Nunca payload. Rate limit por
grant/workspace/tool em store distribuído, caps e kill switch global/per-workspace.

## Critério de aceite

- Logs/traces/audit passam scanner com valores financeiros, CPF, nome, token e
  prompt sentinela em success/error/timeout/rate-limit.
- Audit cobre 100% das calls/falhas sem argumento livre ou resultado.
- Métricas têm baixa cardinalidade; rate limit funciona em ≥2 workers.
- SLO separado do produto: p95 <1 s server-side e success ≥95% como health metrics.
- Alertas têm owner/threshold/runbook; kill switches não exigem deploy.
- Runbook cobre deploy, rollback, revogação, IdP/OpenAI down, cross-tenant/PII e
  recebe co-design `information-architect` + `sre-devops`.
