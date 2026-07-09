---
id: A33.l9
type: lane
title: "Services taxonomy: split de backend/app/services/ em subpacotes por natureza técnica (ADR-285, W6-T07)"
sprint: A33
status: shipped
ship_pr: 855
ship_date: "2026-07-08"
priority: P2
branch_slug: a33-l9-services-taxonomy
adrs: ["[[ADR-285]]"]
depends_on: []
parallel_with: []
tags:
  - type/lane
  - sprint/a33
  - status/shipped
  - priority/p2
  - area/backend
---

# A33.l9 — `services-taxonomy` (W6-T07 do [PLAN-platform-review](../../../archive/PLATFORM_REVIEW_PLAN-2026-07-08.md), cauda da sprint)

## Problema

`backend/app/services/` é um flat namespace que mistura security,
storage, pipeline-adapters e documents. [[ADR-285]] (`Proposto`) desenha
o split em 4 subpacotes por natureza técnica, incremental
(1 subpacote por PR, com shim de import + codemod final).

## Gate de entrada (explícito)

**≤1 PR ativo tocando `backend/app/services/`.** A A32 (`current`) gera
PRs em voo nessa árvore (readers E2, review UX) — esta lane é **cauda**:
só abre quando `gh pr list --search "backend/app/services"` mostrar o
tráfego zerado. Refactor estrutural concorrendo com feature-PRs na mesma
árvore é merge hell garantido.

## Escopo

1. Flip [[ADR-285]] → `Decidido` no primeiro PR de implementação
   (política ADR `Proposto` → `Decidido` no merge).
2. 4 PRs incrementais (`services/security/`, `services/storage/`,
   `services/pipeline/`, `services/documents/`), cada um com shim de
   import compatível.
3. Codemod final remove shims + atualiza imports em todo o repo.
4. Zero mudança de comportamento — diff é de estrutura; testes existentes
   são o gate (nenhum teste novo além de import-smoke).

## Critérios de aceite

1. Gate de entrada verificado e registrado no corpo do PR (lista dos PRs
   em voo no momento do pickup).
2. Suíte completa verde após cada PR incremental (não só no final).
3. `grep -r "from app.services import"` legado zerado após o codemod.
4. PR(s) mergeado(s) em `main` (squash) com CI verde.
