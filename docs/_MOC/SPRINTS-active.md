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
- **W2-W6** abertas conforme [plan/PLATFORM_REVIEW/_README.md](../plan/PLATFORM_REVIEW/_README.md).
- **A11.docreorg** (esta lane): execução do plano [DOC_REORG](../plan/DOC_REORG/_README.md) ([ADR-182](../adr/182-vault-de-documentacao-operacional-obsidian.md)).

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

> Tracks por sprint disponíveis em [`docs/sprint/A6/tracks/`](../sprint/A6/tracks/), [`A7/tracks/`](../sprint/A7/tracks/), [`A8/tracks/`](../sprint/A8/tracks/), [`A11/tracks/`](../sprint/A11/tracks/), [`F7/tracks/`](../sprint/F7/tracks/), [`F9/tracks/`](../sprint/F9/tracks/), [`W5/tracks/`](../sprint/W5/tracks/), [`W6/tracks/`](../sprint/W6/tracks/). Lanes ainda em [BACKLOG](../BACKLOG.md) (legado); migração em F4.
