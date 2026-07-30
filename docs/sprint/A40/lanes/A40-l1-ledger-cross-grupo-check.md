---
id: A40.l1
type: lane
title: "Instrumento: detector de duplicação cross-grupo + baseline congelado"
sprint: A40
plan: PLAN-report-trust
status: planned
priority: P0
branch_slug: a40-l1-ledger-cross-grupo-check
adrs: []
depends_on: []
tags:
  - type/lane
  - sprint/a40
  - status/planned
  - priority/p0
  - area/pipeline
  - area/dx
---

# A40.l1 — `ledger-cross-grupo-check` (instrumento)

## Problema

A conservação do razão fecha em **tol-zero (105/105 grupos-fonte)** e ainda assim
há duplicação material medida no corpus dogfood. Conservação é medida **por
grupo**; a duplicação é **entre** grupos, e cada grupo individualmente fecha.
`dev/certify_ledger_local.py` não tem check cross-grupo — é o furo de método nº 4
da rodada r3.

Esta lane é o **instrumento de medição de toda a A40**: sem ela, KR-B não é
verificável e a [[A40.l2]] fecha verde sem prova. Vem **primeiro** e congela o
baseline **sobre `origin/main`**, antes de qualquer mutação (lição A39 — baseline
pós-mutação mede o próprio fix).

## Escopo

- Detector puro `cross_group_double_count(buckets_e4) -> list[...]` em
  `dev/ledger_conservation.py`, irmão de `investment_double_count`.
- **Chave provenance-free:** `(data, valor_cents, moeda, direction,
  descricao_normalizada)`. Deliberadamente **sem** `banco`/`titular`/`tipo_conta`
  — são justamente os campos que variam entre as pernas do mesmo evento.
- Acoplar ao harness `dev/certify_ledger_local.py`: **reporta, não dedupa**, e
  emite ocorrências whitelisted em **linha separada** (anti-Goodhart do KR-B).
- Medir o blast radius do backfill: contar `transaction_overrides` ancorados em
  row com `titular` vazio (via `override_dual_read.py`). Esse número dimensiona o
  risco da [[A40.l2]].
- **Congelar baseline** do corpus dogfood em `storage/<uuid>/certify/` sobre
  `origin/main`.

## Critério de aceite

- Detector reporta **> 0** no corpus dogfood hoje (se reportar 0, o detector está
  errado — a duplicação foi medida e existe).
- 4 casos em `tests/unit/pipeline/test_cross_group_double_count.py` (fixture
  sintética PII-zero): **(a)** duas pernas do mesmo evento com `tipo_conta`
  variante e `titular` vazio ⇒ **detecta**; **(b)** transferência interna legítima
  (débito na origem + crédito no destino, `direction` oposto) ⇒ **não** detecta;
  **(c)** duas compras idênticas no mesmo dia, mesmo valor, mesma descrição, mesma
  conta ⇒ **não** detecta (duplicata legítima); **(d)** mesmo valor, moedas
  distintas ⇒ **não** detecta.
- Baseline congelado documentado no corpo do PR (path mascarado, fora do git).
- **Zero mudança de comportamento** — nenhum dedup novo, nenhuma escrita.

## Guarda anti-regressão

O caso **(b)** é a guarda que importa: sem `direction` na chave, toda
transferência interna vira falso-positivo em massa e enterra o sinal verdadeiro no
primeiro run. O teste tem de falhar se alguém remover `direction` ou `moeda` da
chave.
