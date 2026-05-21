---
id: A17.l3
type: lane
title: "Informes anuais — L3 financeiro PF (6 bancos + XP Investimentos + Wise multi-moeda)"
sprint: A17
status: planned
priority: P2
branch_slug: a17-l3-financeiro-pf
depends_on:
  - "[[A17.l1]]"
parallel_with:
  - "[[A17.l4]]"
adrs:
  - "[[ADR-238]]"
prompt: "[[TRACK-a17-l3-financeiro-pf]]"
tags:
  - type/lane
  - sprint/a17
  - status/planned
  - priority/p2
  - area/pipeline
  - area/methodology
  - methodology/auvp
---

# A17.L3 — Financeiro PF (bancos + XP Investimentos + Wise)

> **Onda 3 de 4** em [[MOC-sprint-a17]]. Maior volume de PDFs (8 dos 15 do batch). **Inclui Wise (multi-moeda, conta no exterior)** com schema estendido para `moeda` e regras fiscais específicas de conta no exterior.

## Objetivo

Modelar `tipo_informe="financeiro_pf"` ponta a ponta. Snapshot 31/12 alimenta `consolidate_baseline` (E1.5c) — "informe 31/12 vence extrato D+1" quando há divergência. AUVP ganha granularidade por classe de ativo (CDB vs LCI vs Tesouro vs FII vs **conta em moeda estrangeira**).

## PDFs do batch destravados

- Informe Itaú 2025
- Informe Santander 2025
- Informe Caixa 2025
- Informe Nubank 2025
- Informe PicPay 2025
- Informe C6 PF 2025
- Informe XP Investimentos 2025
- **Informe Wise 2025 (multi-moeda, conta no exterior)**
- Informe Einstein (genérico — empregador, possível caso especial)

## Pegadinhas Wise / conta no exterior (documentadas em [[ADR-238]] §D1)

- **Código RFB 62** em `bens_direitos[]` (conta-corrente no exterior, moeda estrangeira) — distinto de 41 doméstico.
- **Conversão PTAX 31/12** via `market_rates` ([[ADR-135]]) — não inventar cotação.
- **Variação cambial não é "rendimento isento"** — é ganho de capital em ME (Lei 9.250/95, DARF GCAP 15%). Não cair no bucket `rendimentos_isentos[]`.
- **Juros em ME** → rendimentos tributáveis recebidos do exterior (carnê-leão, código 13).
- **CBE BACEN** (>USD 1MM em ativos no exterior) → fora do escopo Mathoms; só warning em E5 quando threshold cruzado.

## Critério de aceite

- 8+ PDFs PF do batch classificam como `tipo_informe="financeiro_pf"` com `confidence ≥ 0.7`.
- Snapshot 31/12 alimenta E1.5c sem double-count com extrato de janeiro ano seguinte (regra "informe vence extrato D+1").
- 4 quadros RFB cobertos no schema: `rendimentos_tributaveis[]`, `rendimentos_isentos[]`, `rendimentos_tribexcl[]`, `bens_direitos[]` + campo `moeda` por entrada (default `BRL`).
- IR retido em CDB classifica como **definitivo** (tributação exclusiva, código 06/10) — não gera inferência de "IR a recuperar".
- Rendimento FII isentos PF aparecem em S3 sem assumir ganho de capital (informe não diz isso).
- **Wise (multi-moeda):** saldo USD/EUR convertido por PTAX 31/12; variação cambial **não** cai em isentos; carnê-leão sobre juros em ME flagado; warning CBE BACEN quando soma de ativos no exterior cruza USD 1MM.
- LLM model: Haiku (layout padronizado, custo otimizado).

## Detalhe operacional

[[TRACK-a17-l3-financeiro-pf]].
