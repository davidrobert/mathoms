---
type: moc
title: 00-INDEX — Entrypoint da vault
aliases: ["INDEX", "00-INDEX", "vault-entry"]
---

# 00-INDEX — Entrypoint da vault

> **Editorial.** Atualizado manualmente — não é gerado.

Este é o ponto de entrada da vault Obsidian-friendly de `docs/`. Para LLMs: comece daqui. Para humanos: abra no Obsidian.

## Fluxo de leitura por intenção

| Intenção | Ler primeiro |
|---|---|
| "Onde estamos? sprint atual?" | [SPRINTS-active](SPRINTS-active.md) (editorial) → `_generated/SPRINT_CURRENT.md` |
| "Que planos estão abertos?" | [PLANS-active](PLANS-active.md) (editorial) → `_generated/PLAN_PROGRESS.md` |
| "Que ADRs existem? Onde está X?" | `_generated/ADR_INDEX.md` (auto, agrupado por área) |
| "O que mudou na última semana?" | `_generated/CHANGELOG_RECENT.md` (auto, últimos 14 dias) |
| "Roadmap das fases F0-F11" | `_generated/ROADMAP.md` (auto, populado em F5) |
| "Tudo no sistema" | `_generated/INDEX.md` (auto, 1 linha por nota) |

## Topologia da vault

```
docs/
├── _MOC/                  ← este diretório (índices)
│   ├── 00-INDEX.md        ← você está aqui
│   ├── SPRINTS-active.md  ← editorial: status da sprint
│   ├── PLANS-active.md    ← editorial: planos abertos
│   └── _generated/        ← auto, snapshot test bloqueia drift
├── _schemas/              ← JSON Schemas para frontmatter
├── adr/                   ← 175 ADRs atomizadas (após F2)
├── sprint/                ← lanes + tracks por sprint (após F4)
├── plan/                  ← planos canônicos multi-fase (5 abertos)
├── reference/             ← docs estáveis (PHASES, PRODUCT, ARCHITECTURE, …)
├── archive/               ← planos arquivados, backups pré-shim, manual histórico
├── DECISIONS.md           ← shim → adr/ + _MOC/_generated/ADR_INDEX.md
├── BACKLOG.md             ← shim → _MOC/SPRINTS-active.md + sprint/<X>/lanes/
└── CHANGELOG.md           ← shim → _MOC/_generated/CHANGELOG_RECENT.md + sprint/<X>/changelog/
```

## Como navegar (Obsidian)

- **Graph view:** `Ctrl/Cmd + G` — visualiza wikilinks `[[X]]` entre notas.
- **Backlinks panel:** painel lateral mostra notas que apontam para a atual.
- **Tags panel:** filtra por `type/`, `area/`, `sprint/`, `status/`.
- **Quick switcher:** `Ctrl/Cmd + O` — abre nota por id ou alias.
- **Search:** `Ctrl/Cmd + Shift + F` — full text + tags.

Dataview é **opcional** — vault funciona sem. Habilite só se quiser queries SQL-like sobre frontmatter.

## Estado atual

DOC_REORG ([ADR-182](../adr/182-vault-de-documentacao-operacional-obsidian.md)) **Decidido (Sprint A11.5)** — vault GA. Conteúdo populado:

- **175 ADRs** atomizadas em `adr/` ([índice](_generated/ADR_INDEX.md))
- **74 lanes** em 8 sprints A6/A7/A8/A9/A10/A11/F7/F9 + F11/F12 (futuro) ([sprint atual](_generated/SPRINT_CURRENT.md))
- **62 tracks** em `sprint/<X>/tracks/`
- **5 plans** em `plan/<SLUG>/_README.md` ([status](PLANS-active.md))
- **167 changelog entries** em `sprint/<X>/changelog/` ([últimos 14 dias](_generated/CHANGELOG_RECENT.md))

Próximas evoluções:
- Crítica 1 do PM review (2026-05-07): backfill de taxonomia (`area/*`, `methodology/*`, `priority/*`) em 174 ADRs (hoje só 1 tem taxonomia rica). Depois: domain rules em `reference/rules/<slug>.md`.

## Convenções rígidas (não negociáveis)

- **Filename = ID** (lowercase para slug). `adr/090-decimal-money.md`, não `adr/Decimal-money.md`.
- **Wikilinks `[[X]]`** dentro da vault para alvos que existem; markdown links em `CLAUDE.md`/`README.md`/PRs externos. Durante migração (F1-F4), use markdown links para alvos legados.
- **Frontmatter sempre populado** com schema válido. Gate em `dev/validate_frontmatter.py`.
- **Status muda via frontmatter da nota fonte** — derivações (`_generated/`) são auto.
- **Drift impossível** dentro da vault: snapshot test em `tests/test_doc_indexes_snapshot.py` (após F1.H).
