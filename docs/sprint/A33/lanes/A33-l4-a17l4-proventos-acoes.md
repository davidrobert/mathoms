---
id: A33.l4
type: lane
title: "Fechar A17.l4: integrar proventos de ações (schema/prompt/classifier já existem) ao yield-on-cost em S3"
sprint: A33
plan: null
status: shipped
ship_pr: 830
ship_date: "2026-07-07"
priority: P1
branch_slug: a33-l4-a17l4-proventos-acoes
adrs: ["[[ADR-238]]"]
depends_on: []
parallel_with: ["[[A33.l5]]", "[[A33.l6]]"]
tags:
  - type/lane
  - sprint/a33
  - status/shipped
  - priority/p1
  - area/pipeline
---

# A33.l4 — `a17l4-proventos-acoes` (fechamento da [[A17.l4]])

> **Reconciliado contra o código em 2026-07-07** — diferente do texto
> original da A17 (mai/2026), o grosso já existe:
> `pipeline/llm/schemas/informe_proventos.py` (completo, `Decimal`),
> `config/schemas/informe_proventos.schema.json`,
> `pipeline/llm/prompts/informe_proventos.py` e o classifier
> (`document_classification.py` reconhece `informe_proventos`). O
> residual real é a **integração** — lane pequena.

## Problema

[[A17.l4]] (`in_progress` desde 2026-05-21) construiu
schema/prompt/classifier de proventos, mas o dado extraído **nunca chega
a S3**: `pipeline/domain/services/passive_income_calculator.py` não tem
nenhuma referência a proventos/informe_proventos — yield-on-cost por
ativo (Perini "viver de renda") segue sem a fonte.

## Escopo

1. Integração do payload de proventos com
   [`passive_income_calculator.py`](../../../../pipeline/domain/services/passive_income_calculator.py)
   (yield-on-cost em S3); cuidado documentado em [[ADR-238]]: CNPJ
   pagador ≠ CNPJ fonte.
2. Catálogo: entry `itausa` (se ausente do seed da [[A17.l5]]).
3. Goldens sintéticos PII-zero fim-a-fim (informe → S3), happy + edge
   com JCP + FII.
4. Passo 0 obrigatório: reconciliar o que os PRs da A17 já integraram
   antes de estimar — o texto herdado tem drift comprovado.

## Critérios de aceite

1. Goldens verdes em CI; valores `Decimal` ([[ADR-090]]).
2. Frontmatter de [[A17.l4]] flipa `shipped`; **A17 flipa `done`** no
   mesmo PR (l2 + l4 fecham todo o residual — KR4 da sprint), com
   atualização do [[SPRINTS-active]].
3. PR(s) mergeado(s) em `main` (squash) com CI verde.
