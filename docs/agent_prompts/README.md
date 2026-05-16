# Agent Prompts — shim (movido para `docs/sprint/<X>/tracks/`)

> **Atualizado em 2026-05-07** (F3 do plano [DOC_REORG](../archive/DOC_REORG_PLAN-2026-05-07.md) · ADR-182).

Os 62 tracks que viviam em `docs/agent_prompts/track_*.md` foram migrados para `docs/sprint/<X>/tracks/<slug>.md`, agrupados por sprint e com frontmatter validado por JSON Schema (`docs/_schemas/note-track.schema.json`).

## Onde encontrar cada track

| Sprint | Path | Quantidade |
|---|---|---|
| A6 (sub-fases A6e/A6f/A6g) | [`../sprint/A6/tracks/`](../sprint/A6/tracks/) | 13 |
| A7 | [`../sprint/A7/tracks/`](../sprint/A7/tracks/) | 8 |
| A8 | [`../sprint/A8/tracks/`](../sprint/A8/tracks/) | 1 |
| A11 (sprint atual) | [`../sprint/A11/tracks/`](../sprint/A11/tracks/) | 21 |
| F7 | [`../sprint/F7/tracks/`](../sprint/F7/tracks/) | 1 |
| F9 | [`../sprint/F9/tracks/`](../sprint/F9/tracks/) | 12 |
| W5 (Onda 5 do A11) | [`../sprint/W5/tracks/`](../sprint/W5/tracks/) | 4 |
| W6 (Onda 6 do A11) | [`../sprint/W6/tracks/`](../sprint/W6/tracks/) | 2 |

**Total:** 62 tracks migrados.

## Pickup — onde olhar agora

- **Sprint atual + curating de prioridade:** [`../_MOC/SPRINTS-active.md`](../_MOC/SPRINTS-active.md) (editorial).
- **Lanes abertas para pickup:** [`../_MOC/_generated/SPRINT_CURRENT.md`](../_MOC/_generated/SPRINT_CURRENT.md) (auto-gerado por `dev/build_doc_index.py` filtrado por `status: ready` ou `open`).
- **Estado bruto e legado de lanes (até F4 popular):** [`../BACKLOG.md`](../BACKLOG.md). F4 split desse arquivo em `docs/sprint/<X>/lanes/<id>.md` com frontmatter; após F4, `BACKLOG.md` vira shim de ~30 linhas.

## Convenções de track novo (pós-F3)

- Filename: `<slug>.md` em `docs/sprint/<X>/tracks/` (sem prefixo `track-` no nome do arquivo).
- ID frontmatter: `TRACK-<slug>` (lowercase, hífens).
- Schema: [`docs/_schemas/note-track.schema.json`](../_schemas/note-track.schema.json).
- Status: `ready` (lane aberta), `consumed` (lane mergeada), `cancelled`.

## Archive

[`archive/`](archive/) preservado como histórico (lanes encerradas em sprints muito antigas).

---

> **Por que este shim?** PRs antigos e prompts em sessões anteriores podem linkar para `docs/agent_prompts/track_xyz.md`. Este README mantém o ponto de entrada e redireciona para a estrutura nova.
