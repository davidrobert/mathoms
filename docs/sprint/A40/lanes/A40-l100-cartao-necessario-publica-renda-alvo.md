---
id: A40.l100
type: lane
title: "O cartão rotulado NECESSÁRIO publica a renda-alvo, não o aporte que o motor calcula"
sprint: A40
plan: PLAN-report-trust
status: open
priority: P0
branch_slug: a40-l100-cartao-necessario-publica-renda-alvo
owner: financial-planner
depends_on: []
tags: [type/lane, sprint/a40, status/open, priority/p0, area/frontend, area/financial-planning]
---

# A40.l100 — `cartao-necessario-publica-renda-alvo`

> **Origem:** `F1` da rodada unificada **U3** ([[REPORT-REVIEWS-active]] §r7). Confirmado por
> cético, que **refutou o discriminador da lente** e tornou o achado mais forte.

## O defeito

O cartão rotulado **"APORTE MENSAL NECESSÁRIO"** publica `renda_alvo ÷ 12` — a renda que a
família quer receber na independência —, não o aporte que a atingiria. O motor **já tem** o
PMT correto e ele aparece em cinco superfícies (Projeção, Cone MC, Síntese, a decisão do
plano e o Apêndice C); o número do cartão é o **único ponto do documento fora dessa cadeia**.

## O que o cético derrubou, e por que isso importa

A lente propôs que o cartão passasse a ler o agregado de aporte declarado. **Errado por
sorte:** neste workspace o goal declarado e o PMT coincidem, então o critério de aceite
"batem" passaria nas **duas** implementações. Um cartão rotulado *necessário* tem de ler o
**PMT**, não a meta declarada.

**Critério de aceite (o da lente não discrimina):** fixture em que o goal declarado ≠ PMT.
Se o cartão exibir o goal, ele lê a coisa errada e o rótulo mente do mesmo jeito.
