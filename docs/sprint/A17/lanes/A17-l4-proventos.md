---
id: A17.l4
type: lane
title: "Informes anuais — L4 proventos ações (XP Proventos, Itaúsa)"
sprint: A17
status: in_progress
priority: P2
branch_slug: a17-l4-proventos
depends_on:
  - "[[A17.l1]]"
parallel_with:
  - "[[A17.l3]]"
adrs:
  - "[[ADR-238]]"
prompt: "[[TRACK-a17-l4-proventos-acoes]]"
tags:
  - type/lane
  - sprint/a17
  - status/in-progress
  - priority/p2
  - area/pipeline
  - area/methodology
  - area/report
  - methodology/perini
---

# A17.L4 — Proventos ações (XP Proventos, Itaúsa)

> **Onda 4 de 4** em [[MOC-sprint-a17]]. Onda final — yield-on-cost por ativo enriquece S3.

## Objetivo

Modelar `tipo_informe="proventos_acoes"` ponta a ponta. Eventos por ativo (dividendo, JCP, rendimento FII, bonificação) alimentam `passive_income_calculator.py` com granularidade que S3 hoje só agrega.

## PDFs do batch destravados

- Relatório Proventos XP 2025
- Informe Itaúsa Ações 2025 (caso `proventos_acoes` com 1 ativo)

## Critério de aceite

- XP Proventos e Itaúsa classificam como `tipo_informe="proventos_acoes"` com `confidence ≥ 0.7`.
- Schema modela `proventos[]` com `{ticker, cnpj_pagador, tipo: dividendo|jcp|rend_fii|bonificacao, valor_brl, data_pagamento, ir_retido_brl}`.
- `CNPJ pagador ≠ CNPJ fonte emissora` tratado corretamente (XP informa, mas dividendo veio de WEGE3).
- Bonificação **não** gera bucket de renda (é ajuste de custo, não fluxo).
- S3 "viver de renda" mostra yield-on-cost por ativo (Perini).
- Itaúsa entra em `institutions` como `category=holding`.

## Detalhe operacional

[[TRACK-a17-l4-proventos-acoes]].
