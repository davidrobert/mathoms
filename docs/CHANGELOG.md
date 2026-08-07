<!-- F5.B shim — ADR-182 / DOC_REORG_PLAN F5 — 2026-05-07 -->

# CHANGELOG — shim

> **Não altere histórico aqui.** Para LLMs: leia
> [`CHANGELOG_RECENT`](_MOC/_generated/CHANGELOG_RECENT.md).

## Onde ler agora

| Intenção | Onde |
|---|---|
| "O que mudou nos últimos 14 dias?" | [docs/_MOC/_generated/CHANGELOG_RECENT.md](_MOC/_generated/CHANGELOG_RECENT.md) |
| "Cronologia completa de uma sprint" | `docs/sprint/<X>/changelog/` (1 arquivo por entrada) |
| "Inventário atual" | [docs/_MOC/_generated/DOC_STATS.md](_MOC/_generated/DOC_STATS.md) |

## Quando criar uma entrada

**Não é por PR** — isso valeu até A12; de A34 em diante nenhuma sprint tem
entrada. Hoje marca fechamento de sprint ou cutover grande. Lane registra na
própria lane; fix avulso, no PR. Gotcha ou limite de API que o próximo agente
precisa vai para docstring ([[ADR-143]]) ou emenda de ADR — nunca só no PR.

## Como criar a entrada

1. Crie `docs/sprint/<sprint-atual>/changelog/CHG-YYYY-MM-DD-<SCOPE>.md`.
2. Frontmatter: `id`, `type: changelog-entry`, `date`, `summary`; opcionais `sprint`, `lane`, `adrs`, `prs`, `commits`, `breaking`, `files_touched`, `tags`.
3. Validação: `python3 dev/validate_frontmatter.py docs/sprint/<X>/changelog/<id>.md`.
4. Regenere índice: `python3 dev/build_doc_index.py --inline`.

## Backup pré-shim

Conteúdo completo (6923 linhas, pré-shim): [docs/archive/CHANGELOG-pre-shim-2026-05-07.md](archive/CHANGELOG-pre-shim-2026-05-07.md).
