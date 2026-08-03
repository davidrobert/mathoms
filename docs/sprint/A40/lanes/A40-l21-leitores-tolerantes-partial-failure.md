---
id: A40.l21
type: lane
title: "Leitores tolerantes a partial_failure: run que produziu relatório para de ser pintado como falha"
sprint: A40
plan: PLAN-report-trust
status: open
priority: P0
branch_slug: a40-l21-leitores-tolerantes-partial-failure
adrs:
  - "[[ADR-357]]"
depends_on: []
tags:
  - type/lane
  - sprint/a40
  - status/open
  - priority/p0
  - area/frontend
---

# A40.l21 — `leitores-tolerantes-partial-failure`

> Onda 3 da A40 (§Frente 4 de [[PLAN-report-trust]]), mas **shipa antes da
> [[A40.l18]]** — disciplina expand/contract: leitor tolerante antes de o writer
> emitir. Risco zero, porque hoje o status é **inalcançável em produção**.

## Problema

`partial_failure` já existe no union type
([`frontend/src/lib/api/pipeline.ts`](../../../../frontend/src/lib/api/pipeline.ts))
e já tem rótulo "Parcial" com variante `warning` em
[`frontend/src/lib/format.ts`](../../../../frontend/src/lib/format.ts) — mas a
lógica o trata como **falha** em **7** read sites (9 hits de `partial_failure` em
`frontend/src/` menos as 2 declarações acima):

- `frontend/src/lib/pipelinePhases.ts` — `isFailed: runStatus === "failed" || runStatus === "partial_failure"`. Pinta a fase "Montando seu relatório" de vermelho num run que **produziu** relatório: ativamente enganoso.
- `frontend/src/app/(app)/pipeline/page.tsx` (3 sites) — `lastFailedRun` levanta banner de falha para run que produziu relatório.
- `frontend/src/app/(app)/pipeline/_components/HistoryRow.tsx` (2 sites)
- `frontend/src/app/(app)/pipeline/_components/ActiveRunCard.tsx` — `bg-loss` onde deveria ser `bg-warning`.

E o **toast + redirect** disparam só em `completed`: run parcial hoje não emite
toast nenhum e **abandona o usuário em `/pipeline`** sem dizer que existe
relatório.

## Decisão

| Status | Rótulo | Variante | Ação primária | Contexto |
| --- | --- | --- | --- | --- |
| `completed` | Concluído | success | Ver relatório | — |
| `partial_failure` | **Concluído com ressalva** | warning | **Ver relatório** | "Relatório gerado. O parecer do planejador não foi publicado." |
| `needs_review` | Aguardando revisão | warning | Revisar | "Revisão pendente" |
| `failed` | Falhou | error | Reprocessar | "Falhou em {etapa}" |

Renomear "Parcial" → **"Concluído com ressalva"**: "Parcial" responde *"quanto
rodou?"*; a pergunta do usuário é *"eu tenho relatório?"*. Ação primária **igual**
à de `completed`, porque o resultado é o mesmo objeto.

`partial_failure` e `needs_review` são ambos `warning` — correto, mesma
severidade. Diferencie por ícone e ação, não por cor (forma + cor + texto).

`publish_run_completed`/`publish_run_failed` passam a receber o status real como
parâmetro, em vez de ganhar um terceiro evento.

**Amarra de dead code:** se a [[A40.l18]] escorregar >1 sprint, **reverta esta
lane** — é dead code pelos nossos próprios critérios. O PR do writer referencia
o número deste PR.

## Critério de aceite

- `pipelinePhases.isFailed` **não** contém `partial_failure`.
- Toast + redirect disparam em `partial_failure`, não só em `completed`.
- Fixture de `partial_failure` (o helper de `frontend/tests/lib/format.test.ts`
  já constrói o estado) ⇒ nenhum dos **7** sites renderiza afordância de falha.
- `cd frontend && npm test -- --run` verde; `tsc --noEmit` verde.
- axe-core 0 critical/serious no histórico com run parcial, light e dark.
