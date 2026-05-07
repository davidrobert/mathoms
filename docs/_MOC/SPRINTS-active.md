---
type: moc
title: SPRINTS-active — Sprint corrente + curating de prioridade
aliases: ["SPRINTS-active", "sprints-active"]
---

# SPRINTS-active — Sprint corrente + curating de prioridade

> **Editorial.** Resumo narrativo da sprint atual. Status detalhado: `_generated/SPRINT_CURRENT.md`.

## Sprint atual

**A11 — Platform review execution** (origem 2026-05-06).

32 tasks em 6 ondas, 138 findings consolidados de revisão multi-agente (data-engineer + financial-planner + product-designer + sre-devops + build-vs-buy + senior-cto), 6 ADRs Proposto (ADR-170 a ADR-175).

- **W1** ✅ entregue.
- **W2-W6** abertas conforme [docs/PLATFORM_REVIEW_PLAN.md](../PLATFORM_REVIEW_PLAN.md) (vai migrar para `plan/PLATFORM_REVIEW/_README.md` em F3).
- **A11.docreorg** (esta lane): execução do plano DOC_REORG ([ADR-182](../DECISIONS.md#adr-182--vault-de-documentação-operacional-obsidian-friendly-em-docs)).

## Pickup — antes de pegar lane

1. Confirme `git fetch origin` está atualizado.
2. Veja worktrees ativos: `git worktree list`.
3. Veja branches `agent/*` recentes: `git for-each-ref --sort=-committerdate refs/remotes/origin/agent/`.
4. Lane com slug em uso (worktree OU branch <24h): **não duplique**.
5. Slug das lanes desta sprint: **descritivo curto, kebab-case** (`a11-w2-t01`, `a11-docreorg-f1`, etc.).

## Sprints anteriores (encerradas)

| Sprint | Status | Resumo |
|---|---|---|
| A6 | done | Migração infra+domínio (ADR-097, ADR-111). |
| A7 | done | Config DB cutover (CLI legacy removal). |
| A8 | done | Continuação multi-tenant. |
| A9 | done | Multi-front improvements. |
| A10 | done | `goals.json` cutover final ([ADR-090](../adr/090-decimal-money.md) supersedes parcial). |

> Detalhe completo migra para `sprint/<X>/_README.md` na F4. Hoje (F1), permanece em [BACKLOG](../BACKLOG.md) (legado).
