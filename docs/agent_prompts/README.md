# Agent Prompts — shim (movido para `docs/sprint/<X>/tracks/`)

> **Atualizado em 2026-05-07** (F3 do plano [DOC_REORG](../archive/DOC_REORG_PLAN-2026-05-07.md) · ADR-182).

Os 62 tracks que viviam em `docs/agent_prompts/track_*.md` foram migrados para `docs/sprint/<X>/tracks/<slug>.md`, agrupados por sprint e com frontmatter validado por JSON Schema (`docs/_schemas/note-track.schema.json`).

## Onde encontrar cada track

| Sprint | Path | Quantidade |
|---|---|---|
| A6 (sub-fases A6e/A6f/A6g) | [`../sprint/A6/tracks/`](../sprint/A6/tracks/) | 13 |
| A7 | [`../sprint/A7/tracks/`](../sprint/A7/tracks/) | 8 |
| A8 | [`../sprint/A8/tracks/`](../sprint/A8/tracks/) | 1 |
| A11 | [`../sprint/A11/tracks/`](../sprint/A11/tracks/) | 21 |
| A20 (sprint atual) | [`../sprint/A20/tracks/`](../sprint/A20/tracks/) | 6 |
| F7 | [`../sprint/F7/tracks/`](../sprint/F7/tracks/) | 1 |
| F9 | [`../sprint/F9/tracks/`](../sprint/F9/tracks/) | 12 |
| W5 (Onda 5 do A11) | [`../sprint/W5/tracks/`](../sprint/W5/tracks/) | 4 |
| W6 (Onda 6 do A11) | [`../sprint/W6/tracks/`](../sprint/W6/tracks/) | 2 |

**Total:** 62 tracks migrados (F3) + 6 tracks A20 criados 2026-05-29 + 1 track A6 (`a6g-eslint-max-lines-ratchet`, follow-up A6g.6b) criado 2026-06-09.

## Pickup — onde olhar agora

- **Sprint atual + curating de prioridade:** [`../_MOC/SPRINTS-active.md`](../_MOC/SPRINTS-active.md) (editorial).
- **Lanes abertas para pickup:** [`../_MOC/_generated/SPRINT_CURRENT.md`](../_MOC/_generated/SPRINT_CURRENT.md) (auto-gerado por `dev/build_doc_index.py` filtrado por `status: ready` ou `open`).
- **Estado bruto e legado de lanes (até F4 popular):** [`../BACKLOG.md`](../BACKLOG.md). F4 split desse arquivo em `docs/sprint/<X>/lanes/<id>.md` com frontmatter; após F4, `BACKLOG.md` vira shim de ~30 linhas.

## Convenções de track novo (pós-F3)

- Filename: `<slug>.md` em `docs/sprint/<X>/tracks/` (sem prefixo `track-` no nome do arquivo).
- ID frontmatter: `TRACK-<slug>` (lowercase, hífens).
- Schema: [`docs/_schemas/note-track.schema.json`](../_schemas/note-track.schema.json).
- Status: `ready` (lane aberta), `consumed` (lane mergeada), `cancelled`.

## Prompts de orquestração (meta, não-track)

Prompts reusáveis para sessões em que **um agente orquestrador** coordena especialistas de [`.claude/agents/`](../../.claude/agents/) e leva um conjunto de decisões/features até PR mergeado. Diferente de tracks (1 lane = 1 PR), prompts de orquestração atravessam múltiplas lanes/sprints.

| Prompt | Escopo | Status |
|---|---|---|
| [`_TEMPLATE_orchestrator.md`](_TEMPLATE_orchestrator.md) | Template genérico para qualquer feature multi-especialista | ativo |
| [`orchestrator_a17_a18_a19.md`](orchestrator_a17_a18_a19.md) | Roadmap A17 (informes anuais) → A18 (CRLV + apólices + FIPE) → A19 (card S_PROTECAO 4º pilar AUVP) | ativo (2026-05-21) |
| [`archive/orchestrator_a24_f2f3-2026-06-10.md`](archive/orchestrator_a24_f2f3-2026-06-10.md) | A24 Data Lineage · F2 (de-leak da extração) + F3 (walking skeleton) + F4 (evidencia_path ∥) — fase de risco; pré-revisado (F2-B/F2-DB) | arquivado (sprint done 2026-06-10) |
| [`orchestrator_a25_f5f6f7.md`](orchestrator_a25_f5f6f7.md) | A25 Data Lineage · F5 (reverso) + F6 (produto N1/N2) + F7 (debug LLM) + herdados (cutover K4→E4, decisão flip strict) — pré-revisado (product-manager + senior-cto) | ativo (2026-06-10) |
| [`orchestrator_a26_consolidacao.md`](orchestrator_a26_consolidacao.md) | A26 Data Lineage · consolidação (flip strict + drops M2) — sprint `paused` 2026-07-03, retoma pós-gates de tráfego | ativo (2026-06-16) |
| [`orchestrator_a28_report_trust-2026-07-06.md`](archive/orchestrator_a28_report_trust-2026-07-06.md) | A28 Report Trust · 11 lanes em 3 ondas (fórmulas E5 + loop de dados + apresentação honesta) — 11/11 shipped, sprint `done` | arquivado (2026-07-06) |

**Convenção:** instâncias do template viram `orchestrator_<scope>.md` em `docs/agent_prompts/`. Quando o escopo é entregue (todas as ADRs flippadas `Decidido`), arquivar em [`archive/`](archive/) com data: `git mv orchestrator_<scope>.md archive/orchestrator_<scope>-YYYY-MM-DD.md`.

## Archive

[`archive/`](archive/) preservado como histórico (lanes encerradas em sprints muito antigas + prompts de orquestração arquivados).

---

> **Por que este shim?** PRs antigos e prompts em sessões anteriores podem linkar para `docs/agent_prompts/track_xyz.md`. Este README mantém o ponto de entrada e redireciona para a estrutura nova.
