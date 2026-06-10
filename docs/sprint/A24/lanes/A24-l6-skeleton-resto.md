---
id: A24.l6
type: lane
title: "Data Lineage F3 — skeleton resto: reserva, despesa, total investido"
sprint: A24
plan: PLAN-data-lineage
status: blocked
priority: P1
branch_slug: dl-f3-skeleton-resto
adrs:
  - "[[ADR-279]]"
  - "[[ADR-281]]"
depends_on: ["[[A24.l5]]"]
parallel_with: []
tags:
  - type/lane
  - sprint/a24
  - status/blocked
  - priority/p1
  - area/data-lineage
  - area/pipeline
---

# A24.l6 — `dl-f3-skeleton-resto`

> **Plano:** [[PLAN-data-lineage]] · Onda 3 (F3). Bloqueada por [[A24.l5]]
> (estende o padrão do skeleton aos demais calculadores).

## Objetivo

Estender o `_lineage` field-level do skeleton ([[A24.l5]]) aos demais agregados
de decisão: **reserva de emergência, despesa total, total investido** (rumo a
KR2 6/6 — os restantes fecham em A25).

## Escopo

- `_lineage` nos calculadores correspondentes (`pipeline/domain/services/`),
  mesmo shape/invariantes da l5; entradas novas no `lineage_registry`.
- `check_lineage_sum`/`check_lineage_refs` cobrindo os novos agregados.
- Rebaseline E5 auditável (mesma disciplina G-c da l5).

## Critério de aceite

- 3+ agregados adicionais com lineage fim-a-fim; gates verdes; run 2× byte-idêntico
  (view-model snapshot); invariantes de conservação verdes pós-rebaseline.

## Owner

Mesmo co-design da l5 (`senior-cto` + `data-engineer`); não re-invocar se escopo
idêntico — só se surgir decisão nova.
