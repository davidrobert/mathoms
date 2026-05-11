<!-- F5.B shim — ADR-182 / DOC_REORG_PLAN F5 — 2026-05-07 -->

# CHANGELOG — shim (entries vivem em `docs/sprint/<X>/changelog/`)

> **Este arquivo é um shim.** Entries vivem agora como notas atômicas em `docs/sprint/<X>/changelog/<id>.md` (1 por evento atomizado), com frontmatter validado por JSON Schema (`docs/_schemas/note-changelog-entry.schema.json`).

## Onde ler agora

| Intenção | Onde |
|---|---|
| "O que mudou nos últimos 14 dias?" | [docs/_MOC/_generated/CHANGELOG_RECENT.md](_MOC/_generated/CHANGELOG_RECENT.md) (auto, agregado por dia) |
| "Cronologia completa de uma sprint" | `docs/sprint/<X>/changelog/` (1 arquivo por entrada) |
| "Detalhe de uma entrada específica" | `docs/sprint/<X>/changelog/<id>.md` (frontmatter inclui PR, commits, ADRs, lane) |

## Cronologia top-level por sprint

| Sprint | Período | Entries | Path |
|---|---|---|---|
| A12 (atual) | 2026-05-10 — | 4 | [docs/sprint/A12/changelog/](sprint/A12/changelog/) |
| A11 | 2026-05-06 → 2026-05-10 | 5 | [docs/sprint/A11/changelog/](sprint/A11/changelog/) |
| A10 | 2026-05-06 → 2026-05-07 | 83 | [docs/sprint/A10/changelog/](sprint/A10/changelog/) |
| A8 | abertura 2026-04-27 | 1 | [docs/sprint/A8/changelog/](sprint/A8/changelog/) |
| A7 | até 2026-04-27 | 10 | [docs/sprint/A7/changelog/](sprint/A7/changelog/) |
| F65 (legado) | F6.5 series | 51 | [docs/sprint/F65/changelog/](sprint/F65/changelog/) |
| F0..F9 (legado) | fases originais | 17 | `docs/sprint/F<N>/changelog/` |

**Total atomizado em F5:** 167 entries.

## Como criar uma entrada nova

1. Após mergear PR em `main`, crie `docs/sprint/<sprint-atual>/changelog/CHG-YYYY-MM-DD-<SCOPE>.md`.
2. Frontmatter obrigatório (schema: [`docs/_schemas/note-changelog-entry.schema.json`](_schemas/note-changelog-entry.schema.json)):
   - `id` regex `^CHG-\d{4}-\d{2}-\d{2}-[A-Z0-9-]+$`
   - `type: changelog-entry`, `date: "YYYY-MM-DD"` (com aspas), `summary` (1-2 frases).
   - opcional: `sprint`, `lane` (wikilink), `adrs` (array de wikilinks), `prs` (ints), `commits` (hashes), `breaking` (bool), `files_touched` (int), `tags`.
3. Validação: `python3 dev/validate_frontmatter.py docs/sprint/<X>/changelog/<id>.md`.
4. Regenere índice: `python3 dev/build_doc_index.py --inline`.

## Backup pré-shim

Conteúdo completo (6923 linhas, pré-shim): [docs/archive/CHANGELOG-pre-shim-2026-05-07.md](archive/CHANGELOG-pre-shim-2026-05-07.md).
