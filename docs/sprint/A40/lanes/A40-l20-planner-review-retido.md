---
id: A40.l20
type: lane
title: "PlannerReview representa gerado-e-retido: hoje o estado é inalcançável e a UI mente"
sprint: A40
plan: PLAN-report-trust
status: open
priority: P0
branch_slug: a40-l20-planner-review-retido
adrs:
  - "[[ADR-204]]"
  - "[[ADR-357]]"
depends_on:
  - "[[A40.l18]]"
tags:
  - type/lane
  - sprint/a40
  - status/open
  - priority/p0
  - area/backend
  - area/frontend
---

# A40.l20 — `planner-review-retido`

> Onda 3 da A40 (§Frente 4 de [[PLAN-report-trust]]). Desbloqueia a [[A40.l22]].
>
> **Depende da *decisão*, não do *merge*, da [[A40.l18]]:** o vocabulário de
> status é fixado pela [[ADR-357]] `Proposto`; implementar contra a ADR permite
> mergear em paralelo. Depender do merge serializaria duas semanas por nada.

## Problema

O estado "parecer foi gerado e teve conteúdo retido" **não existe** no modelo:

- `PlannerReview.status` é hardcoded `"Gerado"`
  ([`planner_review_persistence.py:93`](../../../../backend/app/services/planner_review_persistence.py),
  citando [[ADR-204]] §D1).
- `_should_persist_planner_review` retorna `False` quando
  `detail["status"] == "needs_review"`
  ([`pipeline_task.py:1134`](../../../../backend/app/tasks/pipeline_task.py)).

Resultado: em retenção **não existe row**, a API responde 404, e a seção do
relatório cai na copy de "ainda não gerado" — que **mente** para um cliente
premium que pagou pela geração. Nenhuma mudança de copy resolve isso sem tocar o
aggregate.

Segundo defeito no mesmo lugar: `items_gated_count` é **tier gating** (comercial,
ação = comprar). Reutilizá-lo para itens retidos por qualidade (ação =
reprocessar) produz copy contraditória no mesmo card.

## Decisão

1. `PlannerReview.status` passa a representar o desfecho real, com vocabulário
   alinhado ao da [[ADR-357]]. Provável **emenda em [[ADR-204]]** §D1 — é ela que
   fixa o vocabulário hoje.
2. Persistir o aggregate também no desfecho retido (com o artifact degradado que
   a [[ADR-357]] §6 manda commitar).
3. **Contador novo**, separado de `items_gated_count`, para itens retidos por
   qualidade.
4. A API expõe uma **classe fechada de motivo** client-facing
   (ex.: `citacao_nao_confirmada` / `politica_de_conteudo` / `dado_insuficiente`).
   **Nunca** `error_detail` cru — o valor real hoje é
   `"valor monetário na prosa (severidade alta): risco:3"`, vocabulário de
   operador que não pode chegar ao cliente.
5. Persistir a tupla estrutural `(item_type, index, layer, severidade)` no
   summary — hoje o `dropped` do `StrictDecision` perde a camada no caminho e só
   sobra `count`. **Sem prosa e sem valor monetário**, preservando o padrão
   PII-safe já declarado no stage.

## Critério de aceite

- Fixture com item de alta severidade + violação hard ⇒ row de `PlannerReview`
  existe com status de retenção; API 200 (não 404).
- `usePlannerReviewState` ganha o estado correspondente; nenhuma resposta da API
  contém `error_detail` cru, `risco[N]`, nome de camada interna, `stage`, `E5` ou
  `E6`.
- `items_gated_count` inalterado em semântica; contador de retidos é campo
  distinto.
- Snapshot do view-model rebaselinado com `MATHOMS_UPDATE_SNAPSHOT=1`.
- Termo novo registrado em `COPY_GUIDELINES` §2.2 com data, antes de propagar.
