---
id: ADR-045
type: adr
title: "Data lineage via tooltip"
status: Decidido
phase: "F6"
date: "1970-01-01"
relates_to: []
supersedes: []
superseded_by:
  - "[[ADR-281]]"
aliases: ["ADR 045"]
tags:
  - type/adr
  - status/decidido
size_lines: 7
---

# ADR-045 — Data lineage via tooltip

**Status:** Decidido (F6)

**Decisão:** P1 com tooltip simplificado (fonte, banco, data, método det/LLM). Drill-down full para documento/página fica para futuro.

> Superseded por [[ADR-281]] (A23, plano [[PLAN-data-lineage]]) — o drill-down "para futuro" agora é materializado como substrato de lineage field-level. O tooltip permanece como a ponta visível (renderer humano).
