---
id: A33.l4
type: lane
title: "Fechar A17.l4: informes de proventos de ações (XP Proventos + Itaúsa) → yield-on-cost em S3"
sprint: A33
plan: null
status: planned
priority: P1
branch_slug: a33-l4-a17l4-proventos-acoes
adrs: ["[[ADR-238]]"]
depends_on: []
parallel_with: ["[[A33.l5]]", "[[A33.l6]]"]
tags:
  - type/lane
  - sprint/a33
  - status/planned
  - priority/p1
  - area/pipeline
---

# A33.l4 — `a17l4-proventos-acoes` (fechamento da [[A17.l4]])

## Problema

[[A17.l4]] (`planned` desde 2026-05-21) é a última onda da A17: proventos
por ativo (dividendo, JCP, rendimento FII, bonificação) enriquecem S3 com
yield-on-cost (Perini "viver de renda"). O padrão arquitetural
(classifier → sub-schema polimórfico → parser LLM → integração) foi
validado 3× ([[A17.l1]], [[A17.l2]], P1-P2 da [[A17.l3]]) — não há risco
de forma, só execução.

## Escopo (conforme [[ADR-238]] e [[A17.l4]])

1. Sub-schema `informe_proventos.schema.json` — eventos por ativo;
   cuidado documentado: CNPJ pagador ≠ CNPJ fonte.
2. Classifier + parser LLM (layout XP Proventos + Itaúsa).
3. Integração com
   [`passive_income_calculator.py`](../../../../pipeline/domain/services/passive_income_calculator.py)
   (yield-on-cost em S3).
4. Catálogo: entry `itausa` (se ausente do seed da [[A17.l5]]).
5. Goldens sintéticos PII-zero (happy + edge com JCP + FII).

## Critérios de aceite

1. Goldens verdes em CI; valores `Decimal` ([[ADR-090]]).
2. Frontmatter de [[A17.l4]] flipa `shipped`; **A17 flipa `done`** no
   mesmo PR (l2 + l4 fecham todo o residual — KR4 da sprint), com
   atualização do [[SPRINTS-active]].
3. `PROMPT_VERSION` novo nasce semver puro ([[ADR-233]] — coerente com
   [[A33.l3]]).
4. PR(s) mergeado(s) em `main` (squash) com CI verde.
