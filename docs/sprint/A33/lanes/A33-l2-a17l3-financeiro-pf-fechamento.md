---
id: A33.l2
type: lane
title: "Fechar A17.l3: informes financeiro PF P3-P5 (consolidate_baseline + PTAX 31/12 + UI S4 + validações Wise)"
sprint: A33
plan: null
status: open
priority: P1
branch_slug: a33-l2-a17l3-financeiro-pf
adrs: ["[[ADR-238]]", "[[ADR-135]]"]
depends_on: []
parallel_with: ["[[A33.l1]]", "[[A33.l3]]"]
tags:
  - type/lane
  - sprint/a33
  - status/open
  - priority/p1
  - area/pipeline
---

# A33.l2 — `a17l3-financeiro-pf` (fechamento do residual da [[A17.l3]])

## Problema

[[A17.l3]] (informes financeiro PF, maior volume do batch dogfood: 8 de
15 PDFs) está `in_progress` desde 2026-05-24: P1+P2 entregues (#458
schema/prompt + #459 classifier), **P3-P5 pendentes**. A17 está `paused`
com "Bloqueios externos: Nenhum" — o residual é 100% executável.

## Escopo (P3-P5 conforme [[ADR-238]] §D1 e [[A17.l3]])

1. **P3 — `consolidate_baseline` + PTAX:** snapshot 31/12 do informe
   alimenta E1.5c; conversão multi-moeda (Wise: USD/EUR/GBP) via ponteiro
   PTAX 31/12 em `market_rates` ([[ADR-135]]); regra "informe 31/12 vence
   extrato D+1".
2. **P4 — UI S4:** exibição da posição por instituição/moeda no
   relatório. Co-design `product-designer` antes do PR de UI.
3. **P5 — validações Wise:** pegadinhas documentadas em [[ADR-238]] §D1
   (código RFB 62, ganho de capital cambial, CBE BACEN) viram validações
   + `needs_review` quando aplicável. Co-design `financial-planner`
   antes de fixar regra de domínio.

## Critérios de aceite

1. Goldens sintéticos PII-zero cobrindo Wise multi-moeda + banco BRL
   verdes em CI (KR4 — não depende de dogfood do owner).
2. Baseline consolidado usa PTAX 31/12 de `market_rates`, nunca taxa
   hardcoded; dinheiro `Decimal` ponta a ponta ([[ADR-090]]).
3. Frontmatter de [[A17.l3]] flipa `shipped` no PR final da lane.
4. PR(s) mergeado(s) em `main` (squash) com CI verde.
