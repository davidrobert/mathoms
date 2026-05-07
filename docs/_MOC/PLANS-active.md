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
| `PLAN-doc-reorg` | in_progress | A11 | Reorganização documental Obsidian-friendly. ADR canônica [ADR-182](../adr/182-vault-de-documentacao-operacional-obsidian.md). Plano: [plan/DOC_REORG/_README.md](../plan/DOC_REORG/_README.md). |
| `PLAN-platform-review` | in_progress | A11 | 32 tasks em 6 ondas; W1 ✅. [plan/PLATFORM_REVIEW/_README.md](../plan/PLATFORM_REVIEW/_README.md). |
| `PLAN-report-premium` | in_progress | (fora de sprint) | v1 ✅ (10 fases); v2 §17 em ondas A-F paralelizadas. [plan/REPORT_PREMIUM/_README.md](../plan/REPORT_PREMIUM/_README.md). |
| `PLAN-cenarios-estresse` | in_progress | A11 | [plan/CENARIOS_ESTRESSE/_README.md](../plan/CENARIOS_ESTRESSE/_README.md). |

## Pausados (`paused`)

| Plano | Pausado em | Razão |
|---|---|---|
| `PLAN-i18n` | 2026-04-?? | Aguardando produto definir locales prioritários. [plan/I18N/_README.md](../plan/I18N/_README.md). |
| `PLAN-p1-structural` | 2026-04-?? | Substituído por `PLAN-platform-review`. [plan/P1_STRUCTURAL/_README.md](../plan/P1_STRUCTURAL/_README.md). |

## Encerrados (`done`) — em `archive/`

- [`PRODUCT_PLAN-2026-04-15.md`](../archive/PRODUCT_PLAN-2026-04-15.md) (substituído por documentação contínua em `reference/PRODUCT.md` após F5).
- [`CONFIG_CUTOVER_PLAN-2026-04-27.md`](../archive/CONFIG_CUTOVER_PLAN-2026-04-27.md).
- [`GOALS_JSON_CUTOVER_PLAN-2026-05-07.md`](../archive/GOALS_JSON_CUTOVER_PLAN-2026-05-07.md) (Sprint A10).

## Convenções

- **Status canônico** vive no frontmatter de `plan/<SLUG>/_README.md` (`status: in_progress | paused | done | cancelled`).
- **`paused_at` + `pause_reason`** obrigatórios quando `status: paused` (gate em hardening pós-F5).
- **Mover plano** entre estados = editar frontmatter + atualizar esta nota editorial. Drift bloqueado por inspeção visual (gate automático opcional via `dev/check_doc_stale.py` semanal).
- **Plano novo:** crie `docs/plan/<UPPER_SLUG>/_README.md` com frontmatter conforme [`docs/_schemas/note-plan.schema.json`](../_schemas/note-plan.schema.json). Adicione entrada nesta nota editorial.
