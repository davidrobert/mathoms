<!-- F5.B shim — ADR-182 / DOC_REORG_PLAN F5 — 2026-05-07 -->

# CHANGELOG — shim

> **Não altere histórico aqui.** Para LLMs: leia
> [`CHANGELOG_RECENT`](_MOC/_generated/CHANGELOG_RECENT.md) e crie/edite
> `docs/sprint/<X>/changelog/<id>.md`.

## Onde ler agora

| Intenção | Onde |
|---|---|
| "O que mudou nos últimos 14 dias?" | [docs/_MOC/_generated/CHANGELOG_RECENT.md](_MOC/_generated/CHANGELOG_RECENT.md) |
| "Cronologia completa de uma sprint" | `docs/sprint/<X>/changelog/` (1 arquivo por entrada) |
| "Inventário atual" | [docs/_MOC/_generated/DOC_STATS.md](_MOC/_generated/DOC_STATS.md) |

## Cronologia top-level por sprint

Use `docs/sprint/<X>/changelog/`; sprints com entries incluem A12, A11,
A10, A8, A7, F65 e F0..F9 legado. Contagens atuais: [`DOC_STATS`](_MOC/_generated/DOC_STATS.md).

## Como criar uma entrada nova

1. Após mergear PR em `main`, crie `docs/sprint/<sprint-atual>/changelog/CHG-YYYY-MM-DD-<SCOPE>.md`.
2. Frontmatter: `id`, `type: changelog-entry`, `date`, `summary`; opcionais `sprint`, `lane`, `adrs`, `prs`, `commits`, `breaking`, `files_touched`, `tags`.
3. Validação: `python3 dev/validate_frontmatter.py docs/sprint/<X>/changelog/<id>.md`.
4. Regenere índice: `python3 dev/build_doc_index.py --inline`.

## Backup pré-shim

Conteúdo completo (6923 linhas, pré-shim): [docs/archive/CHANGELOG-pre-shim-2026-05-07.md](archive/CHANGELOG-pre-shim-2026-05-07.md).
