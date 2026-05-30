---
id: A22.l5
type: lane
title: "Dedup de dívida cross-year (max(ano) + warning) + schema formal de dividas"
sprint: A22
plan: PLAN-launch-trust
status: open
priority: P1
branch_slug: a22-l5-dedup-divida-cross-year
depends_on: []
parallel_with:
  - "[[A22.l1]]"
  - "[[A22.l3]]"
tags:
  - type/lane
  - sprint/a22
  - status/open
  - priority/p1
  - area/pipeline
---

# A22.l5 — Dedup de dívida cross-year + schema formal de `dividas`

> **Plano:** [[PLAN-launch-trust]] · Frente 1 (F1-O3) · **Should**. Independente
> — arranca no dia 1. **ADR Proposto antes do PR** (schema novo).

## Objetivo

Deduplicar dívida do mesmo financiamento declarada em N anos (hoje conta
dobrado), virando uma `EntityDedupPolicy` sobre o runner entregue em A21.l3.

## Escopo

- Nova policy em `pipeline/domain/services/` (~30 linhas) sobre
  `run_entity_dedup` (contrato `EntityDedup` de A21.l3).
- Chave de série = identidade do financiamento; cross-year usa `max(ano)`
  (saldo devedor mais recente).
- Queda de saldo entre anos é **normal** (amortização) → `DedupWarning` de
  monotonicidade (INV-8), nunca erro. Subida = warning de anomalia.
- **Schema formal de `dividas`** — sai de array livre
  (`baseline_patrimonial.schema.json` L144) para schema tipado com
  `additionalProperties:false`.

## Critério de aceite

- 0 double-count em golden multi-ano de dívida (estende o golden de A21.l2).
- Policy passa nos invariantes INV-1..9 de A21.l1 (conservação, idempotência,
  warning não-silencioso).
- Schema `dividas` aplicado e validado.

## Notas

- Owner: `data-engineer` + `financial-planner` (co-review da regra `max(ano)` —
  é regra patrimonial; invocar ao abrir a lane).
- **ADR Proposto** (schema novo de `dividas` = contrato `config/schemas/`).
- Federa F1-O3 do plano dono.
