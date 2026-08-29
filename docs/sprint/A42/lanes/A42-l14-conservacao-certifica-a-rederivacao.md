---
id: A42.l14
type: lane
title: "Os vereditos de conservação certificam a re-derivação, não o artefato entregue"
sprint: A42
status: planned
priority: P0
branch_slug: a42-l14-conservacao-certifica-a-rederivacao
owner: data-engineer
depends_on: []
adrs:
  - "[[ADR-302]]"
  - "[[ADR-347]]"
tags:
  - type/lane
  - sprint/a42
  - status/planned
  - priority/p0
  - area/dados
---

# A42.l14 — `conservacao-certifica-a-rederivacao`

> **Origem:** `LC6-01` da rodada unificada **U2** ([[LEDGER-CERTIFY-active]] §r6,
> merge `47970706`). Levantado pela lente do razão e **verificado no código** pelo loop
> principal — a descoberta invalidou um cross-check que a própria rodada havia publicado.

## O defeito

`dev/ledger_certify_core.py:247` chama `_conservation(e2_payloads, fresh_e3, e4, result)` —
o E3 é a **re-derivação**. O docstring de `build_report` (`:307`) declara *"a partir das
peças re-derivadas"*. O `persisted_e3` entra em `build_report` e é consumido **só** em
`_drift` (`:322`).

Logo `e3_groups` (`:318`), `e4_buckets`, `investment_collisions` e `natural_key` (`:229`)
**também** descrevem a re-derivação, não o que o run publicou. O `--entregue` cobre **uma**
linha: o numerador da KR-B.

**Agravante não medido:** `_persisted_e3_by_key` é **workspace-latest, não run-scoped** —
existe `_e3_of_run` ao lado e não é usado ali. Os "31 só-no-persistido" podem ser sobra de
runs anteriores; responder isso é parte da lane.

## Por que é P0

No mesmo run o drift é ≠ 0 (4 grupos com count divergente, 31 só-no-persistido). A skill
inteira vinha sendo citada como propriedade do artefato entregue — inclusive por esta
rodada, que se retratou.

## Já refutado — não re-litigue

- *"`coberto-sem-verificação-de-valor` é o único veredito possível, independentemente da
  qualidade do dado"* é **falso**: com `dups == 0` o índice 0 de `_e2e3_checks` emite
  perda-silenciosa; com `count_out > count_in` o índice 2 emite. O veredito é constante
  **enquanto** `count_out < count_in and dups > 0` — estado do **corpus**, não do instrumento.
- A **ordem** dos checks em `dev/ledger_conservation.py:163-180` é **decisão documentada**
  (docstring: *"A ORDEM importa… sub-declaração ⇒ não perda (LC-07)"*). Não é defeito, e a
  rodada vendeu uma como a outra antes de se corrigir.

## Rota sugerida (não é ordem)

`certify` recebe o par (fresco, entregue) e emite **duas** colunas; ou o entregue vira o
default e o fresco vira o drift. Decida e justifique.

**Onde o fix não mora:** `pipeline/**`. Isto é instrumento de review, em `dev/`.

## Critério de aceite

- Toda linha do relatório da skill declara **sobre qual substrato** foi computada.
- O modo entregue cobre conservação, não só o numerador da KR-B.
- Os "31 só-no-persistido" ganham veredito: deste run ou sobra.
