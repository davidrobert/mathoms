<!-- F4.D shim — ADR-182 / DOC_REORG_PLAN F4 — 2026-05-07 -->

# BACKLOG — shim (lanes vivem em `docs/sprint/<X>/lanes/`)

> **Este arquivo é um shim.** As lanes vivem agora como notas atômicas em `docs/sprint/<X>/lanes/<id>.md` (uma por arquivo), com frontmatter validado por JSON Schema (`docs/_schemas/note-lane.schema.json`).

## Onde ler agora

| Intenção | Onde |
|---|---|
| "Sprint atual + lanes prontas pra pickup" | [docs/_MOC/_generated/SPRINT_CURRENT.md](_MOC/_generated/SPRINT_CURRENT.md) (auto, filtrado por `status: ready/open/in_progress`) |
| "Visão narrativa da sprint" | [docs/_MOC/SPRINTS-active.md](_MOC/SPRINTS-active.md) (editorial) |
| "Tabela histórica de lanes por sprint" | `docs/sprint/<X>/lanes.md` ([A6](sprint/A6/lanes.md) · [A7](sprint/A7/lanes.md) · [A8](sprint/A8/lanes.md) · [A9](sprint/A9/lanes.md) · [A10](sprint/A10/lanes.md) · [A11](sprint/A11/lanes.md)) |
| "Diagrama de ondas paralelas" | `docs/sprint/<X>/waves.md` |
| "Detalhe de uma lane específica" | `docs/sprint/<X>/lanes/<id>.md` |
| "Histórico pré-A6 (Bootstrap, F6.5*)" | [docs/sprint/_archive_pre_a6/_README.md](sprint/_archive_pre_a6/_README.md) |

## Pickup — antes de pegar lane

1. `git fetch origin && git worktree list && git for-each-ref --sort=-committerdate refs/remotes/origin/agent/ | head -15`
2. Lane com slug ativo (worktree OU branch <24h) = **tomada**; escolha outra.
3. Detalhe completo do protocolo: [CLAUDE.md §"Antes de pegar uma task"](../CLAUDE.md#antes-de-pegar-uma-task-do-backlog).

## Como criar uma lane nova

1. Crie `docs/sprint/<X>/lanes/<id-com-hifen>-<slug>.md`.
2. Frontmatter obrigatório (schema: [`docs/_schemas/note-lane.schema.json`](_schemas/note-lane.schema.json)):
   - `id` (`A11.W7`, `A6.ux-livestep`, etc.)
   - `type: lane`, `title`, `sprint: A<N>`, `status` (`open`/`in_progress`/`shipped`/...)
   - opcional: `priority`, `branch_slug`, `ship_date`, `ship_pr`, `adrs` (wikilinks), `depends_on`, `parallel_with`, `tags`.
3. Atualize editorial: adicione na tabela de `docs/sprint/<X>/lanes.md` se aplicável.
4. Validação: `python3 dev/validate_frontmatter.py docs/sprint/<X>/lanes/<id>.md`.
5. Regenere índice: `python3 dev/build_doc_index.py --inline`.

## Status canônico

- Sprint corrente: declarada em `docs/sprint/<X>/_README.md` body. `docs/_MOC/SPRINTS-active.md` editorial é a fonte editorial.
- Status de lane: frontmatter `status:` da própria nota. Drift impossível dentro da vault — `_MOC/_generated/` é regenerado por `dev/build_doc_index.py` com snapshot test.

## Backup pré-shim

Conteúdo completo (2358 linhas, pré-shim): [docs/archive/BACKLOG-pre-shim-2026-05-07.md](archive/BACKLOG-pre-shim-2026-05-07.md).

## Gap conhecido (F4.A.followup)

A Fase 4 atomizou **35 lanes** com headings `### <ID> — <Title>` (sprints A6, F7, F11, F12). Lanes em sprints A7-A11 que vivem em **tabelas markdown** (não como H3) ainda não foram migradas para arquivos atômicos — apenas listadas em `docs/sprint/<X>/lanes.md` (editorial). Lane futura `F4.A.followup` vai estender o parser para extrair tabelas; até lá, consulte `docs/archive/BACKLOG-pre-shim-2026-05-07.md` para detalhe textual ou `docs/sprint/<X>/lanes.md` para tabela curada.
