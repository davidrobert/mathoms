---
id: A40.l21
type: lane
title: "Leitores tolerantes a partial_failure: run que produziu relatório para de ser pintado como falha"
sprint: A40
plan: PLAN-report-trust
status: in_progress
priority: P0
branch_slug: a40-l21-leitores-tolerantes-partial-failure
adrs:
  - "[[ADR-357]]"
depends_on: []
tags:
  - type/lane
  - sprint/a40
  - status/in-progress
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

## Correções de premissa medidas na execução (2026-08-05)

O recon de execução varreu `frontend/src/` inteiro e achou **24 sites
materiais**, não 7. Os 7 da §Problema conferem (`rg "partial_failure"` dá 9
hits menos 2 declarações), mas são o subconjunto que cita o literal. Três
correções que mudam o trabalho, não só a contagem:

1. **O site nº 1 está descrito errado.** `pipelinePhases.ts:198 isFailed` não
   pinta a fase de vermelho: o vermelho vem de `ctx.failedPhaseId`, que exige
   um `stage_log` com status `failed` — e a [[ADR-357]] §3 decide que a etapa
   degradada grava `degraded`. O que `isFailed` faz é **vetar** o ramo
   `completed` das 4 fases, que caem em `runStatus === "completed"` e viram
   `pending`: stepper todo cinza, progresso travado. Fix diferente — exige
   mexer também na linha do atalho de fase sem logs e no conjunto de etapas
   terminadas.
2. **Classe de omissão irmã, não enumerada.** Seis sites perguntam "este run
   entregou?" com `=== "completed"` e por isso **excluem** o run parcial:
   toast/redirect do WS, toast/redirect do polling, banner de free tier
   (casava um `completed` mais antigo e citava o `runId` errado), o slot
   transitório da página, o atalho de fase sem logs, e o loop do
   `golden-path.spec.ts`. Fechada com o predicado `isDeliveredRun`.
3. **`degraded` (stage) também é vocabulário novo da [[ADR-357]].** Leitor cego
   a ele mostraria a string crua com ícone `?` e nunca fecharia a fase final.
   Entra nesta lane pela mesma disciplina expand/contract.

**Falso-verde evitado no critério original:** 2 dos 7 sites
(`pipelinePhases.ts:198` e `ActiveRunCard.tsx:107`) só rodam dentro do
`ActiveRunCard`, que a página renderiza apenas sob
`ACTIVE_STATUSES = {pending, running, resuming}` — um teste de página com
fixture parcial passa verde **sem tocá-los**. Precisam de teste direto de
unidade.

**Limite declarado do gate axe:** em jsdom o axe classifica `color-contrast`
como `incomplete`, nunca `violations`, e o helper do repo lê só `violations`.
O par light/dark prova estrutura ARIA/DOM, **não** contraste; contraste real
exige Playwright/Lighthouse.

## Critério de aceite

- `pipelinePhases.isFailed` **não** contém `partial_failure`, e
  `stageLogs.find(status === "failed")` **continua cego** a `degraded`
  (as duas metades, provadas por mutação).
- Toast + redirect disparam em `partial_failure`, nos **dois** caminhos (WS e
  polling), e o desfecho vem do `status` do run — não do nome do evento.
- Fixture `makePartialRun()` (`status`, `report_id` populado e
  `failed_at_stage: null` juntos) ⇒ nenhum site renderiza afordância de falha
  **e** a afordância positiva "Ver relatório" é asserida.
- `cd frontend && npm test -- --run` verde; `tsc --noEmit` verde.
- axe-core 0 critical/serious no histórico com run parcial, light e dark.
- `make update-openapi-snapshot` com **diff vazio** — `partial_failure` já
  está publicado; diff ⇒ [[ADR-357]] §3 foi violada.

## Amarra de reversão (2026-08-05)

O gatilho já é computável e mora no
[§Gate de saída da [[MOC-sprint-a40]]](../_README.md): se a [[A40.l18]] não
tiver mergeado até `date_target` (`2026-08-17`), esta lane é revertida — os
read sites são dead code enquanto nenhum writer emite o status. **Dono:** quem
fizer o pickup seguinte após a data. Esta seção não cria mecanismo novo (seria
segunda fonte de verdade); registra a **receita**, que faltava:

- `git revert <sha-do-squash de #<PR>>` — PR único, frontend-only + 1 teste de
  backend que só pina campo já emitido.
- O que **não** se reverte junto: nada. A lane não tem PR pareado.

Deliberadamente **fora** desta lane: estados de degradação dentro do relatório
e no PDF ([[A40.l22]]), e a UI de "gerado e retido" ([[A40.l20]]).
