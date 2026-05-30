---
id: A21.l2
type: lane
title: "Golden multi-ano anotado + métrica fn_rate/fp_rate"
sprint: A21
plan: PLAN-launch-trust
status: shipped
priority: P0
branch_slug: a21-l2-dedup-golden-metrics
depends_on:
  - "[[A21.l1]]"
parallel_with: []
tags:
  - type/lane
  - sprint/a21
  - status/shipped
  - priority/p0
  - area/pipeline
---

# A21.l2 — Golden multi-ano anotado + métrica fn_rate/fp_rate

> **Plano:** [[PLAN-launch-trust]] §F1-O1.

## Contexto

Hoje a calibração de dedup é qualitativa (*"falso-positivo é pior que
falso-negativo"*) mas **não medida**. Esta lane cria a fixture sintética que
permite medir os dois erros e travar a meta em CI.

## Escopo

- Fixture **zero-PII** em `tests/fixtures/dedup/multi_year_baseline.json` —
  CPFs fictícios com dígito verificador inválido (gate anti-PII do repo).
  Cobre: mesma pessoa em 3 anos, conta conjunta de casal, imóvel em comunhão,
  dívida amortizando, previdência aparecendo como ativo + dedução.
- Bloco `_expected.known_duplicates` anota cada par esperado.
- `tests/test_dedup_recall.py` mede:
  - `fn_rate` = duplicatas reais não fundidas / total de duplicatas reais
  - `fp_rate` = entidades distintas fundidas / total de não-duplicatas

## Critério de aceite

- `fn_rate` ≤ 5% (A21-KR2).
- `fp_rate` = **0%** — red line (A21-KR3).
- Golden consumido pela suíte INV-1..8 de l1.

## Dependências

- Depende de l1 (a suíte de invariantes roda sobre este golden).
