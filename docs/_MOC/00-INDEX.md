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
├── plan/                  ← planos canônicos multi-fase (após F3)
├── reference/             ← docs estáveis (PHASES, RUNBOOK, ARCHITECTURE…)
├── archive/               ← planos arquivados, manual histórico
├── DECISIONS.md           ← shim → adr/ (após F2)
├── BACKLOG.md             ← shim → _MOC/SPRINTS-active.md (após F4)
└── CHANGELOG.md           ← shim → sprint/<X>/changelog/ (após F5)
```

## Como navegar (Obsidian)

- **Graph view:** `Ctrl/Cmd + G` — visualiza wikilinks `[[X]]` entre notas.
- **Backlinks panel:** painel lateral mostra notas que apontam para a atual.
- **Tags panel:** filtra por `type/`, `area/`, `sprint/`, `status/`.
- **Quick switcher:** `Ctrl/Cmd + O` — abre nota por id ou alias.
- **Search:** `Ctrl/Cmd + Shift + F` — full text + tags.

Dataview é **opcional** — vault funciona sem. Habilite só se quiser queries SQL-like sobre frontmatter.

## Estado atual (Fase 1)

A migração documental está em **Fase 1 (Foundation)** do plano DOC_REORG ([ADR-182](../DECISIONS.md#adr-182--vault-de-documentação-operacional-obsidian-friendly-em-docs), status `Proposto`).

Entregáveis F1 (em ordem):
- [x] F1.A — 6 JSON Schemas em `_schemas/`
- [x] F1.B — `dev/build_doc_index.py` v1 + 6 stubs `_MOC/_generated/`
- [x] F1.C — `dev/validate_frontmatter.py`
- [x] F1.D — `dev/check_doc_links.py`
- [x] F1.E — `dev/check_doc_filename_id.py`
- [x] F1.F — `dev/benchmark_doc_token_cost.py` + baseline em `tests/benchmarks/`
- [x] F1.G — ADR exemplo migrada ([[ADR-090]] — Decimal money) + MOCs editoriais
- [ ] F1.H — Pre-commit hooks + snapshot test ativos

A vault só fica **populada** a partir da F2 (175 ADRs migradas) e F4 (lanes em `sprint/<X>/`). Hoje (F1), o vault tem 1 ADR exemplo + stubs gerados — suficiente para validar gates.

## Convenções rígidas (não negociáveis)

- **Filename = ID** (lowercase para slug). `adr/090-decimal-money.md`, não `adr/Decimal-money.md`.
- **Wikilinks `[[X]]`** dentro da vault para alvos que existem; markdown links em `CLAUDE.md`/`README.md`/PRs externos. Durante migração (F1-F4), use markdown links para alvos legados.
- **Frontmatter sempre populado** com schema válido. Gate em `dev/validate_frontmatter.py`.
- **Status muda via frontmatter da nota fonte** — derivações (`_generated/`) são auto.
- **Drift impossível** dentro da vault: snapshot test em `tests/test_doc_indexes_snapshot.py` (após F1.H).
