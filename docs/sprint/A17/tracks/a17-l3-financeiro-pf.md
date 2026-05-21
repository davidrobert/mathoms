---
id: TRACK-a17-l3-financeiro-pf
type: track
title: "Track A17 L3 — Financeiro PF (6 bancos + XP Investimentos): 4 quadros RFB + snapshot 31/12"
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

Onda de maior volume: 7 dos 14 PDFs do batch. Layout RFB padronizado em 4 quadros (tributáveis, isentos, exclusiva, bens/direitos) — LLM Haiku basta. Snapshot 31/12 é o **diferencial técnico** desta lane: alimenta `consolidate_baseline` (E1.5c) com fonte fiscal certificada que vence extrato D+1.

## Decisões já fechadas (não reabrir)

- Tipo canônico `financeiro_pf` — [[ADR-238]] D1. Itaú/Santander/Caixa/Nubank/PicPay/C6 PF/XP Investimentos no mesmo schema.
- Pegadinhas RFB ([[ADR-238]] §Implementação):
  - **IR retido em CDB é definitivo** (tributação exclusiva, código 06/10) — não gera "IR a recuperar".
  - **Saldo em fundo de RF** é informativo; rendimento vai em exclusiva (06) — não duplicar.
  - **Rendimento FII isento PF** mas tributável se vendido com lucro >R$20k/mês — informe não diz isso, não inferir.
- Snapshot 31/12 vence extrato D+1 — [[ADR-238]] D5.
- LLM Haiku (custo otimizado).

## Plano (esqueleto — refinar no pickup)

- **P1** — `informe_pf.schema.json` com 4 quadros RFB + sub-bucket `saldo_31_12_brl[]` por produto (poupança, CDB, LCI/LCA, fundo, conta-corrente).
- **P2** — Classifier `informe_financeiro_pf` (regex content: "Informe de Rendimentos Financeiros", "4 quadros RFB", CNPJs bancos top-20). Adicionar `xpinvestimentos` no catálogo (broker).
- **P3** — Integração com `consolidate_baseline` (E1.5c) — regra "informe 31/12 vence extrato D+1".
- **P4** — UI: S4 ganha detalhamento por classe de ativo (AUVP).

## Critério de aceite (lane completa)

Em [[A17.l3]] §Critério de aceite. Cobre 7 bancos PF + XP Investimentos do batch.
