---
id: A12.cat-learning-loop
type: lane
title: "Categorization Learning Loop — promoção de override em regra"
sprint: A12
status: in_progress
aliases: ["A12.CAT_LEARNING_LOOP", "A12 cat learning loop"]
priority: P1
depends_on: ["[[A11.report-publication]]"]
parallel_with: []
plan_canonical: "[[PLAN-cat-learning-loop]]"
adrs_canonical:
  - "[[ADR-186]]"
  - "[[ADR-188]]"
tags:
  - type/lane
  - sprint/a12
  - status/in-progress
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

1. ☑ **P1 — Schema** (`transaction_overrides.source` +
   `categorization_rules`). Shipped — PR #188, commit `2a36388`, 2026-05-10.
2. ☑ **P2 — Pipeline E4** (`CategorizationRulesV2`). Shipped — PR #194, commit `ab69414`, 2026-05-11.
3. ☐ **P3 — Backend API** (preview/commit/revert + schema evolution). Track ready —
   `cat-learning-loop-p3-backend-api.md`. ADR P3 Proposto: [[ADR-188]] (soft-delete + partial unique + revert_count split).
4. ☐ **Gate dogfood** (entre P3 e P4). Critério: 5 regras criadas no
   workspace do CEO em ≤7d com `revert_rate ≤ 30%`. Custo: 0,5d. Bloqueia
   P4 se falhar — força reavaliar feature antes de investir em UX polida.
5. ☐ **P4 — Frontend `/transactions`** (toast + side-panel +
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

☑ A11.report-publication mergeado em `main` (PR #185, commit `182308a`, 2026-05-10) — pré-requisito atendido.
☑ P1 (Schema) shipped — PR #188, commit `2a36388`, 2026-05-10.
☑ P2 (Pipeline E4) shipped — PR #194, commit `ab69414`, 2026-05-11. [[ADR-186]] Decidida.
☑ P3 (Backend API) shipped — 4 PRs (#195 docs, #196 schema, #197 endpoints, #198 async/perf), último commit `d660daf`, 2026-05-11. [[ADR-188]] Decidida (consolida 7 ressalvas do gate triple P2 + R1-R8 data-eng PR2).
☐ **Gate dogfood** — próximo passo. Owner: CEO + product-manager. 0,5d setup + 7d wall-clock. Critérios em [docs/reference/RUNBOOK.md §9](../../../reference/RUNBOOK.md). Bloqueia P4.
☐ P4 (Frontend `/transactions`) — track criado se gate dogfood passar. Owner: product-designer + frontend. ~4d eng.
