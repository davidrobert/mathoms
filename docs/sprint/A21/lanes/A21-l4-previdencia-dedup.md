---
id: A21.l4
type: lane
title: "Dedup previdência PGBL/VGBL (ativo × dedução fiscal, cross-axis)"
sprint: A21
plan: PLAN-launch-trust
status: shipped
priority: P1
branch_slug: a21-l4-previdencia-dedup
depends_on:
  - "[[A21.l3]]"
parallel_with: []
tags:
  - type/lane
  - sprint/a21
  - status/shipped
  - priority/p1
  - area/pipeline
---

# A21.l4 — Dedup previdência PGBL/VGBL (cross-axis)

> **Plano:** [[PLAN-launch-trust]] §F1-O4.
> **⚠️ ADR Proposto antes do PR** (invariante de domínio novo, cross-axis com [[ADR-236]]).

## Contexto

O mesmo plano de previdência aparece **duas vezes** no baseline: como **ativo**
(posição patrimonial) **e** como **dedução fiscal** (base PGBL). Sem dedup
cross-axis, infla o PL e distorce a recomendação de aporte. Gap descoberto no
co-design (financial-planner) — é double-count **visível ao cliente**, por isso
launch-blocking.

## Escopo

- Nova `EntityDedupPolicy` para previdência sobre o runner de l3.
- Reconcilia os dois eixos: conta como **1 ativo**; a dedução PGBL alimenta a
  base fiscal **sem somar ao PL**.
- Respeita o invariante [[ADR-236]]: base PGBL = renda tributável PF (folclore
  "receita×32%" rejeitado).

## Critério de aceite

- Teste verde: plano de previdência conta 1× como ativo; dedução não soma ao PL
  (A21-KR4).
- Coberto pela suíte INV-1..8 (l1) e medido no golden (l2 inclui caso de
  previdência ativo+dedução).

## Dependências

- Depende de l3 (é uma policy sobre o contrato `EntityDedup`).
- **ADR Proposto** antes do PR.
