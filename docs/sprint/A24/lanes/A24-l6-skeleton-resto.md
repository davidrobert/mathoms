---
id: A24.l6
type: lane
title: "Data Lineage F3 — skeleton resto: reserva, despesa, total investido"
sprint: A24
plan: PLAN-data-lineage
status: shipped
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
  - status/shipped
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

## Resultado (shipped 2026-06-10, #590)

KR2 **4/6**: `reserva_emergencia.total_liquida` ([[ADR-218]]) ·
`fluxo_caixa.despesa_total` ([[ADR-137]]) · `investimentos.total` ([[ADR-193]])
resolvíveis via `dev/explain_number.py`; 88 testes no skeleton; rebaseline do
view-model 100% aditivo em commit isolado.

**Follow-up rastreado (A25):** cobertura K4 em E4 é 0% hoje — F1 estampa
`natural_key` só no write-path E2; E3/E4 não propagam (classifier emite
`transaction_hash` v1, shim deprecated). O nó de despesa emite
`member_hashes: []` + `signals.k4_coverage="partial"` (fallback contratual);
o mecanismo K4 completo está implementado e coberto em unit, e **ativa sozinho
no cutover natural_key→E4** ([[A23.l4]] M2, A25). Teto inline (~200 hashes)
medido: 1 hash potencial na fixture — sem decisão de edge-table necessária.

## Owner

Agente da lane; co-design herdado da l5 (`senior-cto` + `data-engineer`).
