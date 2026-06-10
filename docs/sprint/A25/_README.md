---
id: MOC-sprint-a25
type: moc
title: "Sprint A25 — Data Lineage: reverso + produto N1/N2 + debug LLM"
aliases: ["A25", "Sprint A25"]
sprint_status: candidate
date: "2026-06-09"
theme: "data-lineage"
---

# Sprint A25 — Data Lineage: reverso + produto N1/N2 + debug LLM

> **Status:** `candidate` — fast-follow do plano [[PLAN-data-lineage]], abre quando
> [[MOC-sprint-a24]] (walking skeleton, G3/KR2 1/6) fechar. Perfil distinto de A24:
> query reversa + UI cliente + agente LLM de debug, com eval de injeção de bug.
>
> **Plano dono:** [[PLAN-data-lineage]] ([plan/DATA_LINEAGE/_README.md](../../plan/DATA_LINEAGE/_README.md)).

## Escopo

- **F5 — lineage reverso:** query "números que dependem da fonte X"; `artifact_lineage_edge`
  + stage terminal `materialize_lineage` (retenção [[ADR-241]]: último run por workspace).
- **F6 — produto N1/N2 (drill-down "por que esse número?"):** selo `<MonetaryValue/>`
  + popover "Como chegamos a esse número" (4 verbos 1ª pessoa); UI cliente régua
  COPY_GUIDELINES §6.3. Visual snapshot só aqui (G-h).
- **F7 — substrato de debug LLM + eval:** renderer de trace linearizada, `lineage_diff`,
  tools (`explain_number`/`expand_node`/`trace_source`), eval de injeção determinística
  (KR1 `localization_accuracy@node ≥ 85%`; KR3 `tool_iterations_p95 ≤ 6`).

## Abertura

Lanes abrem quando A24 fechar (G3 verde). KRs KR1/KR3 nascem em F7.
