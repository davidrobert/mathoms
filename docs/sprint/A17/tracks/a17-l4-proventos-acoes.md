---
id: TRACK-a17-l4-proventos-acoes
type: track
title: "Track A17 L4 — Proventos ações (XP Proventos, Itaúsa): eventos por ativo + yield-on-cost S3"
lane: "[[A17.l4]]"
sprint: A17
status: ready
created_at: "2026-05-21"
consumed_at: null
agent_role: senior-cto
tags:
  - type/track
  - sprint/a17
  - status/ready
  - area/pipeline
  - area/methodology
  - area/report
  - methodology/perini
---

# Track A17 L4 — Proventos ações

> **Lane:** [[A17.l4]] · **ADR canônica:** [[ADR-238]] D1-D5 · **Pré-requisito:** [[A17.l1]] mergeada · **Paralela com:** [[A17.l3]]
> · **Branch prefix:** `agent/a17-l4-proventos/*` · **Tamanho estimado:** ~3-4d eng em 2-3 PRs

## Briefing

Onda final. Yield-on-cost por ativo em S3 — Perini "viver de renda". Schema diferente das outras ondas: **eventos por ativo** (dividendo, JCP, rendimento FII, bonificação), não por instituição. Itaúsa é caso de `proventos_acoes` com 1 ativo (não holding como tipo separado).

## Decisões já fechadas (não reabrir)

- Tipo canônico `proventos_acoes` — [[ADR-238]] D1. Itaúsa fundida aqui (não tipo `dividendos_holding` separado).
- Pegadinhas ([[ADR-238]] §Implementação):
  - **CNPJ pagador ≠ CNPJ fonte emissora.** Corretora informa, mas dividendo veio da companhia (ex.: WEGE3). Para conferência RFB é o pagador.
  - **Bonificação não é renda** — é ajuste de custo médio. Não cair em bucket de fluxo.
  - **Rendimento FII isento PF** mas tributável se vendido com lucro >R$20k/mês — informe não diz isso, não inferir.

## Plano (esqueleto — refinar no pickup)

- **P1** — `informe_proventos.schema.json` com `proventos[]: {ticker, cnpj_pagador, tipo: dividendo|jcp|rend_fii|bonificacao, valor_brl, data_pagamento, ir_retido_brl}` + opcional `posicao_31_12[]` (custódia).
- **P2** — Classifier `informe_proventos_acoes` (regex content: "Relatório de Proventos", "Aviso aos acionistas", "Rendimentos de FII"). Adicionar `itausa` (holding) no catálogo.
- **P3** — Integração [`passive_income_calculator.py`](../../../../pipeline/domain/services/passive_income_calculator.py) + S3 yield-on-cost por ativo.

## Critério de aceite (lane completa)

Em [[A17.l4]] §Critério de aceite. Cobre XP Proventos + Itaúsa do batch.
