---
id: A12.cat-learning-loop
type: lane
title: "Categorization Learning Loop — promoção de override em regra"
sprint: A12
status: planned
aliases: ["A12.CAT_LEARNING_LOOP", "A12 cat learning loop"]
priority: P1
depends_on: ["[[A11.report-publication]]"]
parallel_with: []
plan_canonical: "[[PLAN-cat-learning-loop]]"
adrs_canonical:
  - "[[ADR-186]]"
tags:
  - type/lane
  - sprint/a12
  - status/planned
  - priority/p1
  - area/categorization
  - area/methodology
---

# A12.cat-learning-loop — Categorization Learning Loop

> Lane multi-fase. Plano canônico:
> [PLAN-cat-learning-loop](../../../plan/CAT_LEARNING_LOOP/_README.md).
> Decisão arquitetural: [[ADR-186]].
>
> **Pré-requisito externo:** [[A11.report-publication]] ([[ADR-187]])
> deve mergear antes de iniciar P2 (Pipeline E4). P1 (Schema) pode rodar
> em paralelo com a impl de A11.report-publication.

## Origem

Sessão 2026-05-10 — gap identificado: edição de categoria em
`/transactions` não propaga para `/config → Categorias`. Co-design com
`financial-planner` + `product-designer` produziu modelo híbrido
C-light + D-forte. Review `product-manager` (sessão 2026-05-10) moveu
de A11 para A12 (A11 já sobrecarregada com PLATFORM_REVIEW + COMPETITIVE +
DOC_REORG; feature nova de 19d roubaria capacidade de hardening de produção).

## Sequência (MVP V1)

1. **P1 — Schema** (`transaction_overrides.source` +
   `categorization_rules`). Track criado quando A12 abrir + P0 externo
   da `A11.report-publication` estiver em curso.
2. **P2 — Pipeline E4** (`CategorizationRulesV2`). Track criado quando
   P1 mergear E `A11.report-publication` mergear.
3. **P3 — Backend API** (preview/commit/revert). Track criado quando P2
   mergear.
4. **Gate dogfood** (entre P3 e P4). Critério: 5 regras criadas no
   workspace do CEO em ≤7d com `revert_rate ≤ 30%`. Custo: 0,5d. Bloqueia
   P4 se falhar — força reavaliar feature antes de investir em UX polida.
5. **P4 — Frontend `/transactions`** (toast + side-panel +
   highlight-to-extract). Track criado se gate dogfood passou.

## V2 (pós-tração)

P5 (Sugestões pendentes em `/config → Categorias`) e P6 (Detector
offline + telemetria avançada + alertas SRE) saem do MVP por decisão PM
sessão 2026-05-10. Razão: dogfood não precisa de inbox auto-curado; alertas
SRE são prematuros sem dados de uso. Voltam em sprint posterior se MVP
provar tração.

Telemetria mínima (4 contadores) entra no P3 backend, não em P6 dedicado.

## Branch prefix

`agent/cat-learning-loop-p<N>-<slug>/<yyyyMMdd-HHmm>` por fase. Slug da
fase casa com nome do track (`cat-learning-loop-p1-schema`,
`cat-learning-loop-p2-pipeline`, etc.).

## Gate de promoção entre fases

Cada fase mergeia em `main` com:

- Suíte verde (pytest backend + pipeline; Vitest + Playwright se UI).
- Snapshot OpenAPI atualizado (se tocou endpoint).
- Goldens E4 inalterados (workspace sem regras promovidas) em P2+.
- Review do especialista designado (ver tabela em
  [PLAN §Handoffs](../../../plan/CAT_LEARNING_LOOP/_README.md#handoffs-e-revisão)).

## Status atual

☐ candidate (sprint A12 abre quando A11 fechar)
☐ Pré-req externo: [[A11.report-publication]] ainda em ready
☐ P1-P4: tracks criados quando sprint abrir
