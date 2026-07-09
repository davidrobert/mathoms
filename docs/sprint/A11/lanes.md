# Sprint A11 — Lanes (histórico)

> Tabela estática das waves da Sprint A11. Detalhe operacional (acceptance_criteria, files_touched, paired_doc_task, risk/rollback) está em [docs/plan/PLATFORM_REVIEW/_README.md](../../plan/PLATFORM_REVIEW/_README.md). Para arquivos atomicos por task, ver [`lanes/<id>.md`](lanes) populado por F4.A.

| Wave | Title | Status | Tasks | Esforço |
|---|---|---|---|---|
| [[A11.w1]] | Hot patches + ADR backfill | shipped | 8 | 5d |
| [[A11.w2]] | Pipeline + DB hardening | shipped | 6 | 7d |
| [[A11.w3]] | Auth + LLM ops + Email | blocked (4/5 done · resta W3-T02 owner-gated) | 5 | 12d |
| [[A11.w4]] | Production readiness | blocked (1 done · 2 parciais · residual owner-gated) | 5 | 10d |
| [[A11.w5]] | Frontend + Methodology | open (5 tasks, escopo reduzido — spike 2026-07-08) | 5 | 10d |
| [[A11.w6]] | Tech debt cleanup | open (6/7 done · resta W6-T01 residual) | 6 | 12d |

## Status detalhado por wave

| Wave | Plano | Depende de | Status |
|---|---|---|---|
| W1 | [PLAN §W1](../../plan/PLATFORM_REVIEW/_README.md#wave-1--hot-patches--adr-backfill-sprint-imediato-5-dias-dev) | — | ✅ entregue 2026-05-06/07 |
| W2 | [PLAN §W2](../../plan/PLATFORM_REVIEW/_README.md#wave-2--pipeline--db-hardening-sprint-1-7-dias-dev) | W1 P0 ✅ | ✅ entregue 2026-05-20 (6/6) |
| W3 | [PLAN §W3](../../plan/PLATFORM_REVIEW/_README.md#wave-3--auth--llm-ops--email-sprint-2-12-dias-dev) | W2 ✅ | ◐ 4/5 done — resta W3-T02 (owner-gated: Resend EU) |
| W4 | [PLAN §W4](../../plan/PLATFORM_REVIEW/_README.md#wave-4--production-readiness-sprint-3-10-dias-dev) | W3 ✅ + drill backup | ◐ 1 done + 2 parciais — residual owner-gated (R2, Coolify, Sentry, status page) |
| W5 | [PLAN §W5](../../plan/PLATFORM_REVIEW/_README.md#wave-5--frontend--methodology-sprint-4-10-dias-dev) | W1 ✅ (parcial) | ☐ pickup real — escopo reduzido por task (spike 2026-07-08) |
| W6 | [PLAN §W6](../../plan/PLATFORM_REVIEW/_README.md#wave-6--tech-debt-cleanup-sprint-5-12-dias-dev) | — | ◐ 6/7 done — resta W6-T01 residual (sub-schemas E4 + wire ADR-090) |

> Reconciliado 2026-07-08 (sessão de closure A11) — fonte por task:
> [PLAN Index](../../plan/PLATFORM_REVIEW/_README.md#index).

> Tracks operacionais por task em [`tracks/`](tracks).
