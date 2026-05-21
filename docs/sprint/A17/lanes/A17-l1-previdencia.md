---
id: A17.l1
type: lane
title: "Informes anuais — L1 previdência privada (PGBL/VGBL, BrasilPrev e seguradoras)"
sprint: A17
status: shipped
priority: P1
branch_slug: a17-l1-previdencia
depends_on: []
parallel_with: []
adrs:
  - "[[ADR-238]]"
ship_prs:
  - "https://github.com/davidrobert/mathoms/pull/402"
  - "https://github.com/davidrobert/mathoms/pull/403"
  - "https://github.com/davidrobert/mathoms/pull/404"
  - "https://github.com/davidrobert/mathoms/pull/406"
  - "https://github.com/davidrobert/mathoms/pull/407"
ship_date: "2026-05-21"
prompt: "[[TRACK-a17-l1-previdencia-privada]]"
tags:
  - type/lane
  - sprint/a17
  - status/shipped
  - priority/p1
  - area/pipeline
  - area/methodology
  - area/report
  - methodology/perini
  - methodology/cerbasi
  - methodology/auvp
---

# A17.L1 — Previdência privada (PGBL/VGBL)

> **Onda 1 de 4** em [[MOC-sprint-a17]]. Valida padrão arquitetural completo: classifier + schema-base polimórfico + parser LLM + `FiscalAnalyzer` polimórfico + UI integration. L2-L4 replicam.

## Objetivo

Modelar `tipo_informe="previdencia_privada"` ponta a ponta. Destrava `PgblStatus.capacidade_disponivel` ([[ADR-189]]) para workspaces sem E1.6 — caso de uso "comecei a usar Mathoms em janeiro/fevereiro, antes de declarar IR".

## PDFs do batch destravados

- Informe BrasilPrev 2025 (PGBL)

## Critério de aceite

- BrasilPrev 2025 classifica como `tipo_informe="previdencia_privada"` com `confidence ≥ 0.7`.
- Workspace **sem** `extract_irpf_full` mas com informe BrasilPrev mostra `PgblStatus.capacidade_disponivel > 0` quando houver renda tributável inferida.
- S8 Previdência renderiza KPI PGBL com footnote "Cálculo informativo. Confira com seu contador antes de declarar."
- VGBL nunca conta como capacidade PGBL (validado por teste unitário em `tests/test_fiscal_analyzer.py`).
- 13 PDFs do batch fora desta onda continuam em `.other` sem regressão.

## Detalhe operacional

[[TRACK-a17-l1-previdencia-privada]].
