---
id: A18.l1
type: lane
title: "Comprovantes de Bem — L1 CRLV-e (Certificado de Registro e Licenciamento de Veículo)"
sprint: A18
status: shipped
ship_prs:
  - "https://github.com/davidrobert/mathoms/pull/388"
  - "https://github.com/davidrobert/mathoms/pull/391"
  - "https://github.com/davidrobert/mathoms/pull/412"
  - "https://github.com/davidrobert/mathoms/pull/414"
  - "https://github.com/davidrobert/mathoms/pull/416"
  - "https://github.com/davidrobert/mathoms/pull/417"
ship_date: "2026-05-22"
priority: P1
branch_slug: a18-l1-crlv
depends_on: []
parallel_with: []
adrs:
  - "[[ADR-239]]"
prompt: "[[TRACK-a18-l1-crlv-veiculos]]"
tags:
  - type/lane
  - sprint/a18
  - status/shipped
  - priority/p1
  - area/pipeline
  - area/persistence
---

# A18.L1 — CRLV-e (Comprovante de Bem · Veículo)

> **Onda 1 de 3** em [[MOC-sprint-a18]]. **Lane gateway:** valida padrão arquitetural (tabela `vehicles` + reconciliação assíncrona + classifier content-first + parser LLM Haiku + stage `extract_comprovantes_bens`) que L2 e L3 reutilizam.

## Objetivo

Modelar `tipo_comprovante="crlv"` ponta a ponta. Tabela `vehicles` materializa identidade canônica `(workspace_id, placa, renavam)` imutável ([[ADR-225]] padrão); CRLV é a primeira fonte; apólice (L2) e IRPF G02 (existente) reconciliam via FK opcional assíncrona.

## PDFs do batch destravados

- CRLV NMAX_DAV0351 (Yamaha NMAX 160 2018)
- CRLV NMAX160_STH2C88 (Yamaha NMAX 160 Connected ABS 2024)
- CRLV Toro_GDK6A27 (Fiat Toro Cabine Dupla Ultra 2.0 16V 4×4 2022)

## Critério de aceite

- 3 CRLVs do batch classificam como `tipo_comprovante="crlv"` com `confidence ≥ 0.7`.
- Tabela `vehicles` criada via migration Alembic; UNIQUE `(workspace_id, placa)`; CHECK `renavam ~ '^[0-9]{9,11}$'`.
- Identidade `(workspace_id, placa, renavam)` é **imutável** ([[ADR-225]]); colisão placa↔renavam diferente → `needs_review=true` sem merge automático.
- Reconciliação assíncrona com IRPF G02 — fuzzy marca+modelo+ano confidence ≥ 0,85 = auto-merge; < 0,85 = `needs_review`.
- `baseline_patrimonial.veiculos_consolidados[]` deixa de ser fonte (vira projection com FK `veiculo_id`).
- Pegadinhas dos PDFs do batch (NMAX 2018 vs NMAX 2024 ABS Connected — modelos similares, FIPE codes distintos: 8271020 vs 827125-9) não geram falsos positivos de dedupe.
- 18 PDFs do batch fora desta lane (15 informes A17 + 3 apólices L2) continuam em seu fluxo sem regressão.
- LLM Haiku (padrão simples de CRLV-e, custo otimizado).

## Detalhe operacional

[[TRACK-a18-l1-crlv-veiculos]].
