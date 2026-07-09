# Sprint A11 — Lanes (histórico)

> Tabela estática das waves da Sprint A11. Detalhe operacional (acceptance_criteria, files_touched, paired_doc_task, risk/rollback) está em [docs/archive/PLATFORM_REVIEW_PLAN-2026-07-08.md](../../archive/PLATFORM_REVIEW_PLAN-2026-07-08.md). Para arquivos atomicos por task, ver [`lanes/<id>.md`](lanes) populado por F4.A.

| Wave | Title | Status | Tasks | Esforço |
|---|---|---|---|---|
| [[A11.w1]] | Hot patches + ADR backfill | shipped | 8 | 5d |
| [[A11.w2]] | Pipeline + DB hardening | shipped | 6 | 7d |
| [[A11.w3]] | Auth + LLM ops + Email | shipped (4/5 done · W3-T02 transferido p/ LAUNCH_TRUST) | 5 | 12d |
| [[A11.w4]] | Production readiness | shipped (residual owner-gated transferido p/ LAUNCH_TRUST) | 5 | 10d |
| [[A11.w5]] | Frontend + Methodology | shipped (T01-T03 no closure #882/#883/#884 · T04/T05 → backlog) | 5 | 10d |
| [[A11.w6]] | Tech debt cleanup | shipped (6/7 done · W6-T01 residual → backlog) | 6 | 12d |

## Status detalhado por wave

| Wave | Plano | Depende de | Status |
|---|---|---|---|
| W1 | [PLAN §W1](../../archive/PLATFORM_REVIEW_PLAN-2026-07-08.md#wave-1--hot-patches--adr-backfill-sprint-imediato-5-dias-dev) | — | ✅ entregue 2026-05-06/07 |
| W2 | [PLAN §W2](../../archive/PLATFORM_REVIEW_PLAN-2026-07-08.md#wave-2--pipeline--db-hardening-sprint-1-7-dias-dev) | W1 P0 ✅ | ✅ entregue 2026-05-20 (6/6) |
| W3 | [PLAN §W3](../../archive/PLATFORM_REVIEW_PLAN-2026-07-08.md#wave-3--auth--llm-ops--email-sprint-2-12-dias-dev) | W2 ✅ | ✅ 4/5 done — W3-T02 (Resend) transferido p/ LAUNCH_TRUST §F2 |
| W4 | [PLAN §W4](../../archive/PLATFORM_REVIEW_PLAN-2026-07-08.md#wave-4--production-readiness-sprint-3-10-dias-dev) | W3 ✅ + drill backup | ✅ 1 done + 2 parciais — residual owner-gated (R2, Coolify, Sentry, status page) transferido p/ LAUNCH_TRUST §F2 |
| W5 | [PLAN §W5](../../archive/PLATFORM_REVIEW_PLAN-2026-07-08.md#wave-5--frontend--methodology-sprint-4-10-dias-dev) | W1 ✅ (parcial) | ✅ T01/T02/T03 entregues no closure (#882/#883/#884); T04/T05 → backlog candidates |
| W6 | [PLAN §W6](../../archive/PLATFORM_REVIEW_PLAN-2026-07-08.md#wave-6--tech-debt-cleanup-sprint-5-12-dias-dev) | — | ✅ 6/7 done — W6-T01 residual → backlog candidate |

> **Sprint fechada `done` 2026-07-08** (emenda [[ADR-228]]) — fonte por task:
> [PLAN Index](../../archive/PLATFORM_REVIEW_PLAN-2026-07-08.md#index).

> Tracks operacionais por task em [`tracks/`](tracks).
