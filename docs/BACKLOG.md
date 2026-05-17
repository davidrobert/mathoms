<!-- F4.D shim — ADR-182 / DOC_REORG_PLAN F4 — 2026-05-07 -->

# BACKLOG — shim

> **Não altere estado aqui.** Para LLMs: comece por
> [`SPRINT_CURRENT`](_MOC/_generated/SPRINT_CURRENT.md) para pickup e por
> [`SPRINTS-active`](_MOC/SPRINTS-active.md) para narrativa. Lanes vivem em
> `docs/sprint/<X>/lanes/<id>.md`.

## Onde ler agora

| Intenção | Onde |
|---|---|
| "Sprint atual + lanes prontas pra pickup" | [docs/_MOC/_generated/SPRINT_CURRENT.md](_MOC/_generated/SPRINT_CURRENT.md) |
| "Visão narrativa da sprint" | [docs/_MOC/SPRINTS-active.md](_MOC/SPRINTS-active.md) (editorial) |
| "Detalhe histórico ou específico" | `docs/sprint/<X>/lanes.md` ou `docs/sprint/<X>/lanes/<id>.md` |
| "Histórico pré-A6" | [docs/sprint/_archive_pre_a6/_README.md](sprint/_archive_pre_a6/_README.md) |

## Pickup — antes de pegar lane

1. `git fetch origin && git worktree list`.
2. Confira branches `agent/*` recentes antes de duplicar slug.
3. Protocolo completo: [CLAUDE.md](../CLAUDE.md).

## Como criar uma lane nova

1. Crie `docs/sprint/<X>/lanes/<id-com-hifen>-<slug>.md`.
2. Frontmatter: `id`, `type: lane`, `title`, `sprint`, `status`; opcionais `priority`, `branch_slug`, `ship_date`, `ship_pr`, `adrs`, `depends_on`, `parallel_with`, `tags`.
3. Atualize editorial: adicione na tabela de `docs/sprint/<X>/lanes.md` se aplicável.
4. Validação: `python3 dev/validate_frontmatter.py docs/sprint/<X>/lanes/<id>.md`.
5. Regenere índice: `python3 dev/build_doc_index.py --inline`.

## Backup pré-shim

Conteúdo completo (2358 linhas, pré-shim): [docs/archive/BACKLOG-pre-shim-2026-05-07.md](archive/BACKLOG-pre-shim-2026-05-07.md).

## Nota histórica

A migração ADR-182 preservou o backup completo em `docs/archive/`.
Inventário atual da vault: [docs/_MOC/_generated/DOC_STATS.md](_MOC/_generated/DOC_STATS.md).
