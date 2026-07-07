---
id: A31.l2
type: lane
title: "calibrar MAX_SETTABLE_BUDGET_USD com unit economics (US$ 1.000 → US$ 300)"
sprint: A31
plan: PLAN-internal-admin
status: shipped
ship_pr: 818
ship_date: "2026-07-07"
priority: P2
branch_slug: a31-l2-max-budget-calibracao
adrs: ["[[ADR-173]]"]
depends_on: []
parallel_with: ["[[A31.l1]]"]
tags:
  - type/lane
  - sprint/a31
  - status/shipped
  - priority/p2
  - area/internal-ops
---

# A31.l2 — `max-budget-calibracao` (constante + emenda datada ADR-173)

## Problema

`MAX_SETTABLE_BUDGET_USD = US$ 1.000` (clamp anti-typo do editor de budget,
A30.l1, `backend/app/schemas/admin.py`) foi chute conservador. Débito: valor
sem racional é guardrail-teatro.

## Decisão (financial-planner, 2026-07-07)

**US$ 300/mês interino.** Racional: ~50× o P99 de uso real observado
(US$ 5,57/mês no workspace mais pesado, 32 calls); corta o blast radius de
typo em 70% vs US$ 1.000; mantém-se ordem de grandeza acima da faixa de
COGS que um premium R$ 50-150 comporta (US$ 2-8/workspace/mês a 20-30% da
receita). Alto o bastante para nunca atrapalhar operação legítima
(multi-declarante incluso), baixo o bastante para pegar o dedo gordo.

**Recalibrar quando:** (a) houver pricing — o clamp vira função do tier top
(ex.: 10× o budget do plano mais caro), não constante; (b) P99 real passar
de ~US$ 30/mês; (c) troca de modelo com pricing materialmente diferente.

## Escopo

1. `MAX_SETTABLE_BUDGET_USD` → `Decimal("300.00")` em
   `backend/app/schemas/admin.py` (comentário aponta a emenda da ADR-173).
2. **Emenda datada na [[ADR-173]]** (padrão ADR-027: `## Emenda … 2026-07-07`
   + `amended_at` no frontmatter + blockquote de sinal no topo — gate
   `check_adr_amendment_signal.py`): registra o clamp do editor, o valor, o
   racional acima e os gatilhos de recalibração.
3. Ajustar teste `test_reject_above_sanity_cap` se fixado em valor (usa a
   constante — verificar).

## Critérios de aceite

1. Constante trocada; testes do editor de budget verdes
   (`backend/tests/internal_ops/test_update_workspace_llm_budget.py` +
   `backend/tests/api/admin/test_workspace_llm_budget.py` — o reject de
   `999999` continua cobrindo).
2. Emenda ADR-173 passa `check_adr_amendment_signal` + `validate_frontmatter`.
3. Racional cita a consulta ao `financial-planner` (não valor inventado).
4. PR mergeado em `main` (squash) com CI verde.
