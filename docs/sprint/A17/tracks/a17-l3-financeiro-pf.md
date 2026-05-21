---
id: TRACK-a17-l3-financeiro-pf
type: track
title: "Track A17 L3 — Financeiro PF (6 bancos + XP Investimentos + Wise multi-moeda): 4 quadros RFB + snapshot 31/12 + conta no exterior"
lane: "[[A17.l3]]"
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
  - methodology/auvp
---

# Track A17 L3 — Financeiro PF

> **Lane:** [[A17.l3]] · **ADR canônica:** [[ADR-238]] D1-D5 · **Pré-requisito:** [[A17.l1]] mergeada · **Paralela com:** [[A17.l4]]
> · **Branch prefix:** `agent/a17-l3-financeiro-pf/*` · **Tamanho estimado:** ~5-7d eng em 4 PRs (alto volume de instituições)

## Briefing

Onda de maior volume: 8 dos 15 PDFs do batch. Layout RFB padronizado em 4 quadros (tributáveis, isentos, exclusiva, bens/direitos) para bancos PF — LLM Haiku basta. Snapshot 31/12 é o **diferencial técnico** desta lane: alimenta `consolidate_baseline` (E1.5c) com fonte fiscal certificada que vence extrato D+1.

**Wise é caso especial de PF com conta multi-moeda no exterior** — mesmo schema, mas com campo `moeda` propagando (BRL default, USD/EUR/GBP para Wise) e tratamento fiscal distinto (código RFB 62, PTAX 31/12 via `market_rates`, variação cambial = GCAP não isento, juros = carnê-leão).

## Decisões já fechadas (não reabrir)

- Tipo canônico `financeiro_pf` — [[ADR-238]] D1. Itaú/Santander/Caixa/Nubank/PicPay/C6 PF/XP Investimentos + **Wise** no mesmo schema.
- Pegadinhas RFB ([[ADR-238]] §Implementação):
  - **IR retido em CDB é definitivo** (tributação exclusiva, código 06/10) — não gera "IR a recuperar".
  - **Saldo em fundo de RF** é informativo; rendimento vai em exclusiva (06) — não duplicar.
  - **Rendimento FII isento PF** mas tributável se vendido com lucro >R$20k/mês — informe não diz isso, não inferir.
- **Pegadinhas Wise / conta no exterior** ([[ADR-238]] §D1):
  - Código RFB **62** em `bens_direitos[]` (distinto de 41 doméstico).
  - Conversão PTAX 31/12 via [[ADR-135]] `market_rates` — não inventar cotação.
  - **Variação cambial NÃO é "rendimento isento"** — é ganho de capital ME (Lei 9.250/95, DARF GCAP 15%).
  - Juros em ME → rendimentos tributáveis recebidos do exterior (carnê-leão, código 13).
  - CBE BACEN (>USD 1MM) → fora do escopo Mathoms; só warning em E5.
- Snapshot 31/12 vence extrato D+1 — [[ADR-238]] D5.
- LLM Haiku (custo otimizado, mesmo para Wise — layout consistente).

## Plano (esqueleto — refinar no pickup)

- **P1** — `informe_pf.schema.json` com 4 quadros RFB + sub-bucket `saldos_31_12[]` por produto (`{tipo: poupanca|cdb|lci|fundo|conta_corrente|conta_exterior, descricao, saldo, moeda}`) + campo `moeda` em `rendimentos_*[]` (default `BRL`).
- **P2** — Classifier `informe_financeiro_pf` (regex content: "Informe de Rendimentos Financeiros", "4 quadros RFB", CNPJs bancos top-20, **+ regex Wise** com "Wise Brasil", "saldo em moeda estrangeira", CNPJ Wise Brasil). Adicionar `xpinvestimentos` no catálogo (broker). Wise já está no seed (`wise`).
- **P3** — Integração com `consolidate_baseline` (E1.5c) — regra "informe 31/12 vence extrato D+1". Para Wise: aplicar PTAX 31/12 do `market_rates` na conversão.
- **P4** — UI: S4 ganha detalhamento por classe de ativo (AUVP). Conta em ME aparece como classe própria com flag "exterior".
- **P5** — Validações fiscais específicas Wise: variação cambial → flag para GCAP (não isento); juros em ME → flag para carnê-leão; saldo total no exterior > USD 1MM → warning CBE em E5.

## Critério de aceite (lane completa)

Em [[A17.l3]] §Critério de aceite. Cobre 7 bancos PF + XP Investimentos + **Wise (multi-moeda, conta exterior)** do batch.
