---
id: A38.l5
type: lane
title: "TypeRule cdbdetalhes rouba extrato de conta com `\\bCDB\\b` na descrição de transação"
sprint: A38
status: shipped
ship_date: "2026-07-23"
ship_pr: 1028
priority: P1
branch_slug: a38-l5-typerule-cdbdetalhes
adrs: []
depends_on: []
tags:
  - type/lane
  - sprint/a38
  - status/shipped
  - priority/p1
  - area/backend
  - area/pipeline
---

# A38.l5 — `typerule-cdbdetalhes-required-forte` (achado #5)

## Problema (evidência verificada 2026-07-22)

Em `backend/app/services/classification/type_classifier.py`, a TypeRule
`cdbdetalhes` (priority 18) tem required fraco: `\bCDB\b` sozinho. Extrato de
conta corrente Itaú com a linha de aplicação automática
`APLICACAO CDB COFRINHOS` é classificado como `cdbdetalhes` (conf 0.7) — a
regra vence a `extratoconta` (priority 30) por prioridade. Consequência no
corpus: o doc roteia para parser de CDB `.xls` inexistente para PDF → cai no
E2-llm, quando `parse_itau` o atenderia. Qualquer extrato com movimentação de
CDB no período reproduz o bug.

## Escopo

- Endurecer o required da `cdbdetalhes`: `\bCDB\b` **+** marcador de posição
  de investimento (`Dispon[ií]vel\s*para\s*Resgate|Rentabilidade|Valor\s*
  (Aplicado|Bruto|L[íi]quido)`) como required composto, e/ou `exclude` quando
  marcador de extrato de conta presente (`extrato conta|SALDO\s*DO\s*DIA|
  lan[çc]amentos`).
- Teste de regressão antes do fix: preview sintético de extrato com
  `APLICACAO CDB COFRINHOS` → `extratoconta`; preview sintético de posição
  CDB → `cdbdetalhes` (fixtures existentes de CDB continuam passando).

## Critério de aceite

- Corpus local (harness [[A38.l1]]): extrato Itaú 2025-S2 →
  `extratoconta` conf 1.0 (KR-B).
- Fixtures de classification existentes verdes; docs CDB legítimos não mudam
  de tipo (KR-E).

## Risco

Baixo. Mudança local numa TypeRule; anti-regressão coberta.
