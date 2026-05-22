---
id: A17.l5
type: lane
title: "LLM Hardening — W4-T00 seed expandido institution_catalog (alta renda PJ)"
sprint: A17
plan: PLAN-llm-prompts-hardening
status: in_progress
priority: P0
branch_slug: a17-l5-llm-institution-seed
parallel_with:
  - "[[A17.l3]]"
adrs:
  - "[[ADR-137]]"
tags:
  - type/lane
  - sprint/a17
  - status/in-progress
  - priority/p0
  - area/llm
  - area/persistence
---

# A17.L5 — Seed expandido de `institution_catalog` (W4-T00)

> **Onda 0 do plano [[PLAN-llm-prompts-hardening]]**, antecipada para A17 L3 conforme revisão PM (2026-05-22). Lane independente; W4-T01 (`InstitutionCatalogProvider` protocol) em A20 consome este seed.

## Objetivo

`institution_catalog` ([[ADR-137]]) hoje cobre os 8 bancos hardcoded em prompts LLM (`itau, santander, bradesco, c6bank, btgpactual, rico, nubank, inter`). **Não cobre o público-alvo alta renda PJ típico** — gap identificado pelo `financial-planner` na revisão do plano.

Seed expandido (mínimo 15 entries) destrava:

- Wise/Avenue/Nomad no [[A17.l3]] (Financeiro PF) — exposição cambial AUVP.
- W4-T01 do plano [[PLAN-llm-prompts-hardening]] — injection do catálogo no user prompt vs. hardcoded no system prompt.

## Cobertura mínima (revisão `financial-planner`)

| Categoria | Instituições | `category` |
|---|---|---|
| **Corretoras alta renda** | XP Investimentos, BTG Pactual digital (separado do `btgpactual` institucional), Genial, Modal, Ágora, Toro, Warren | `corretora` |
| **Conta global USD** | Avenue, Inter Invest USA, Nomad, Stake | `conta_global` |
| **Migrações históricas** | Pi (Santander), NuInvest (ex-Easynvest) | `corretora` |
| **Conta-pagamento (fluxo de caixa)** | Inter Pag, PicPay Invest, Mercado Pago Conta | `conta_pagamento` |
| **Cooperativas** | Sicoob, Sicredi | `cooperativa` |

Total: ~18 entries novas.

## Critério de aceite

- Migration Alembic em `backend/alembic/versions/` que extends seed de `b6c7d8e9f0a1_seed_institution_catalog.py`.
- Cada entry tem `category` populado (necessário para W4-T01 discriminar bancos vs. seguradoras vs. corretoras).
- 18+ entries novas em produção; total ≥30 entries no `institution_catalog`.
- Goldens de [[A17.l3]] usam `Wise`, `Avenue`, `XP` quando aplicável.
- `python3 dev/check_doc_links.py` e `pytest backend/tests -q -k "institution"` verdes.

## Coordenação

Independente do resto do plano [[PLAN-llm-prompts-hardening]]. Pode ser puxada em qualquer momento de A17. Beneficia [[A17.l3]] imediatamente quando mergeada.

## Detalhe operacional

Apenas migration + seed. Sem mudança em code de aplicação. PR pequeno (~0.5d eng-time).
