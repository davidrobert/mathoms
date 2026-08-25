---
id: A40.l84
type: lane
title: "O invariante é declarado global em comentário e enforçado num só ponto de entrada: run completa sobre review que ninguém aprovou"
sprint: A40
plan: PLAN-deterministic-authority
status: open
priority: P0
branch_slug: a40-l84-guard-na-camada-errada
adrs:
  - "[[ADR-404]]"
  - "[[ADR-359]]"
depends_on: []
tags:
  - type/lane
  - sprint/a40
  - status/open
  - priority/p0
  - area/backend
  - area/pipeline
---

# A40.l84 — Guard na camada errada (RV8-08)

> **O comentário declara o invariante como se fosse global; o código o enforça
> num ponto de entrada.** O outro caminho está documentado no runbook como ação
> operacional, o que normaliza o contorno.

## O fato, medido no r8

`pipeline_service.resume_pipeline_run` (`:292`) chama `_flip_run_to_resuming`
(`:262`), cujo único predicado é `run.status != PipelineRunStatus.needs_review`.
**Zero consulta a `stage_reviews`.**

O predicado que importa — `count(StageReview.status == pending) > 0 →
ConflictError` — existe **apenas** em
`backend/app/application/pipeline_run/resume_run.py:21-33`, a camada HTTP.

E `backend/app/tasks/pipeline_task.py:1129-1132` **declara o invariante como se
fosse global**:

> *`StageReview` fica do lado do CONTROLE de propósito ([[ADR-404]]): `resume_run`
> só libera a retomada com zero reviews `pending`… falha silenciosa pior que a
> barulhenta.*

**A falha silenciosa é o estado corrente.** No DB de dogfood,
`stage_reviews ⋈ pipeline_runs` tem os pares: `(completed, approved) 8` ·
`(failed, approved) 4` · **`(completed, pending) 2`** · `(completed, edited) 1`.

Os dois `(completed, pending)` são o **r7 e o r8** — os dois últimos runs da skill
`pipeline-review`, que retoma pelo service. O r7 é o **baseline de comparação do
r8**: todo veredito de regressão daquela revisão foi medido contra um run que
completou sobre review não resolvida.

`docs/reference/runbooks/stuck_pipeline_runs.md:197` documenta o service como ação
operacional — o contorno não é acidente de um agente, é caminho documentado.

## O que a lane tem de decidir, não só mover

**Mover o predicado quebra a skill `pipeline-review`, e isso é o comportamento
desejado.** Ela retoma pelo service justamente para não precisar aprovar. Depois
do fix, ela **não vai conseguir** — e é assim que tem de ser: um run retido por
`review_reason` só deve completar depois que alguém decidiu.

Mas quebrar em silêncio troca um defeito por outro. O escopo inclui **dar à skill
uma ação explícita de aprovação** (ou de recusa registrada), senão o próximo
`pipeline-review` trava sem saber por quê e o operador volta a contornar — agora
por um caminho ainda menos visível.

**Segundo ponto de decisão: o fecho.** Hoje nada impede
`(completed, pending)` de nascer por outro caminho. Um predicado só na entrada
volta a ser guard de porta. `_finalize_run` recusar `completed` com
`StageReview.pending` do mesmo run é o que fecha a **classe**; sem isso a lane
fecha a instância.

**Terceiro: as 2 rows históricas.** Decida explicitamente — anotar, backfillar ou
deixar. Row que documenta um estado que o código passa a proibir vira armadilha
para quem consultar depois. Registre a escolha.

## Restrição

A ordem da [[ADR-404]] permanece: controle commita primeiro e sozinho; o
analítico depois, em sessão própria, fail-open. O predicado novo é **de
controle** e vive na mesma sessão da transição — é exatamente onde a ADR o quer.
Há hook de pre-commit (`Diagnóstico não divide sessão com transição de run`).

Cuidado com a compensação: `_dispatch_resume` já reverte `resuming → needs_review`
em falha de dispatch ([[ADR-359]] §2 — compensar é **reverter**, não marcar
`failed`). O predicado novo deve **recusar antes** de flipar o status, não flipar
e compensar depois.

## Critério de aceite

**Corretude** — `resume_pipeline_run` levanta com review `pending`, e o run
permanece `needs_review` (não vira `resuming` nem `failed`). Teste por entrada:
um pelo service, um pela rota HTTP.

**Completude** — o par `(completed, pending)` deixa de ser alcançável por
**qualquer** caminho. Teste de fecho em `_finalize_run`, não só de entrada.

**Consistência** — o comentário de `pipeline_task.py:1129-1132` passa a descrever
o que o código faz. Hoje ele afirma cobertura que a medição refuta; se o fix não
alcançar todos os caminhos, o comentário é **corrigido para a verdade menor**, não
mantido na maior.

**Precisão** — o erro nomeia o que falta: qual stage, quantas reviews pendentes e
o que fazer. "Conflict" sozinho manda o operador para o mesmo contorno.

**Prova de fecho (predicado do r9)** — `SELECT` do par `(completed, pending)` não
cresce; e o próximo `pipeline-review` completa **com** aprovação registrada, não
por contorno.

## Delegação

`senior-cto` decide onde o predicado mora e se `_finalize_run` entra no escopo.
`sre-devops` revisa o runbook, que hoje ensina o contorno.

## Rastro

RV8-08 do §r8 de [[PIPELINE-REVIEWS-active]] (run `d0f6260a`, 2026-08-24) —
achado que a **própria revisão** produziu ao se apoiar no contorno. Medições
refeitas nesta lane.
