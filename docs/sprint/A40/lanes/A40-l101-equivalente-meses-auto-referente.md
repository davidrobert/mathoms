---
id: A40.l101
type: lane
title: "O conserto da folga deixou `equivalente_meses_poupanca` auto-referente"
sprint: A40
plan: PLAN-report-trust
status: open
priority: P1
branch_slug: a40-l101-equivalente-meses-auto-referente
owner: financial-planner
depends_on: []
adrs: ["[[ADR-422]]"]
tags: [type/lane, sprint/a40, status/open, priority/p1, area/pipeline, area/financial-planning]
---

# A40.l101 — `equivalente-meses-auto-referente`

> **Origem:** `F2` da **U3** ([[REPORT-REVIEWS-active]] §r7) · triagem
> **`REGRESSÃO-DE-CONSERTO`**, confirmada por cético como P1 não-inerte.

## O defeito

A [[A40.l94]] ([[ADR-422]]) consertou a folga mensal — verificado, **segura**. Mas o campo
irmão ficou **auto-referente**: o denominador virou a mesma referência mensal de consumo da
qual o numerador é subconjunto (medido no PDF: o numerador é **45,4%** do denominador). O
campo colapsa e a leitura de "quantos meses de poupança este gasto custou" deixa de medir o
que o rótulo promete.

## O que o cético derrubou

A alegação de que a razão ser **superlinear** é defeito em si **cai** — razão
`gasto ÷ superávit` é a forma legítima de todo indicador tipo dívida/renda. O defeito é o
**polo** e o colapso, não a curvatura.

**Classe:** conserto que fecha o defeito principal e deixa o irmão lendo a base nova. É a
razão de a rodada perguntar por `REGRESSÃO-DE-CONSERTO` explicitamente.
