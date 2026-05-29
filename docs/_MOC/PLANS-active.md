---
type: moc
title: PLANS-active — Planos canônicos abertos
aliases: ["PLANS-active", "plans-active"]
---

# PLANS-active — Planos canônicos abertos

> **Editorial curto.** Status, contagens e lanes: [`PLAN_PROGRESS`](_generated/PLAN_PROGRESS.md).

## Olhar primeiro

| Plano | Por que importa agora |
|---|---|
| [`PLAN-launch-trust`](../plan/LAUNCH_TRUST/_README.md) | Três frentes launch-blocking: confiabilidade do número (F1), produção (F2→platform-review), Parecer defensável (F3→planner-review). |
| [`PLAN-platform-review`](../plan/PLATFORM_REVIEW/_README.md) | Revisão A11: segurança, dados e produção. |
| [`PLAN-cat-learning-loop`](../plan/CAT_LEARNING_LOOP/_README.md) | Categorização A12: pipeline, backend e UX. |
| [`PLAN-report-premium`](../plan/REPORT_PREMIUM/_README.md) | Superfície principal de produto. |
| [`PLAN-cenarios-estresse`](../plan/CENARIOS_ESTRESSE/_README.md) | Cenários de estresse e regras. |
| [`PLAN-llm-prompts-hardening`](../plan/LLM_PROMPTS_HARDENING/_README.md) | LGPD/ADR-090/telemetria nos 9 prompts LLM — A17/A18/A20. |

## Pausados relevantes

| Plano | Pausado em | Razão |
|---|---|---|
| `PLAN-i18n` | 2026-04-?? | Aguardando produto definir locales prioritários. [plan/I18N/_README.md](../plan/I18N/_README.md). |
| `PLAN-p1-structural` | 2026-04-?? | Substituído por `PLAN-platform-review`. [plan/P1_STRUCTURAL/_README.md](../plan/P1_STRUCTURAL/_README.md). |

## Encerrados

- [`PRODUCT_PLAN-2026-04-15.md`](../archive/PRODUCT_PLAN-2026-04-15.md).
- [`CONFIG_CUTOVER_PLAN-2026-04-27.md`](../archive/CONFIG_CUTOVER_PLAN-2026-04-27.md).
- [`GOALS_JSON_CUTOVER_PLAN-2026-05-07.md`](../archive/GOALS_JSON_CUTOVER_PLAN-2026-05-07.md).
- [`DOC_REORG_PLAN-2026-05-07.md`](../archive/DOC_REORG_PLAN-2026-05-07.md).

## Convenções

- Status canônico: frontmatter de `plan/<SLUG>/_README.md`.
- Plano novo: crie `docs/plan/<UPPER_SLUG>/_README.md` conforme [`note-plan.schema.json`](../_schemas/note-plan.schema.json) e adicione aqui.
