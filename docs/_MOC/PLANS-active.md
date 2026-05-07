---
type: moc
title: PLANS-active — Planos canônicos abertos
aliases: ["PLANS-active", "plans-active"]
---

# PLANS-active — Planos canônicos abertos

> **Editorial.** Status declarado por humano. Detalhe agregado: `_generated/PLAN_PROGRESS.md`.

## Em execução (`in_progress`)

| Plano | Status | Sprint atual | Resumo |
|---|---|---|---|
| `PLAN-doc-reorg` | in_progress | A11 | Reorganização documental Obsidian-friendly. ADR canônica [ADR-182](../DECISIONS.md#adr-182--vault-de-documentação-operacional-obsidian-friendly-em-docs); exemplo migrado: [ADR-090](../adr/090-decimal-money.md). Plano: [DOC_REORG_PLAN.md](../DOC_REORG_PLAN.md) (migra para `plan/DOC_REORG/_README.md` em F3). |
| `PLAN-platform-review` | in_progress | A11 | 32 tasks em 6 ondas; W1 ✅. Ver [docs/PLATFORM_REVIEW_PLAN.md](../PLATFORM_REVIEW_PLAN.md). |
| `PLAN-report-premium` | in_progress | (fora de sprint) | v1 ✅ (10 fases); v2 §17 em ondas A-F paralelizadas. Ver [docs/REPORT_PREMIUM_PLAN.md](../REPORT_PREMIUM_PLAN.md). |
| `PLAN-cenarios-estresse` | in_progress | A11 | Ver [docs/CENARIOS_ESTRESSE_PLAN.md](../CENARIOS_ESTRESSE_PLAN.md). |

## Pausados (`paused`)

| Plano | Pausado em | Razão |
|---|---|---|
| `PLAN-i18n` | 2026-04-?? | Aguardando produto definir locales prioritários. Ver [docs/I18N_PLAN.md](../I18N_PLAN.md). |
| `PLAN-p1-structural` | 2026-04-?? | Substituído por `PLAN-platform-review`. Ver [docs/P1_STRUCTURAL_PLAN.md](../P1_STRUCTURAL_PLAN.md). |

## Encerrados (`done`) — em `archive/`

- `PRODUCT_PLAN-2026-04-15.md` (substituído por documentação contínua em `reference/PRODUCT.md` após F5).
- `CONFIG_CUTOVER_PLAN-2026-04-27.md`.
- `GOALS_JSON_CUTOVER_PLAN-2026-05-07.md` (Sprint A10).

## Convenções

- **Status canônico** vive no frontmatter de `plan/<SLUG>/_README.md` (`status: in_progress | paused | done | cancelled`).
- **`paused_at` + `pause_reason`** obrigatórios quando `status: paused` (gate em F1.G.4 / hardening pós-F5).
- **Mover plano** entre estados = editar frontmatter + atualizar esta nota editorial. Drift bloqueado por inspeção visual (gate automático opcional via `dev/check_doc_stale.py` semanal).
- **Plano fora de `docs/plan/`** ainda existe na F1-F2 (legado em `docs/*PLAN.md`); F3 move tudo.
