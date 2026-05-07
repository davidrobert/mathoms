---
id: ADR-071
type: adr
title: "Playwright workspace isolation: email unique por worker"
status: Decidido
date: "2026-04-15"
relates_to: []
supersedes: []
superseded_by: []
aliases: ["ADR 071"]
tags:
  - area/frontend
  - area/multitenancy
  - area/testing
  - status/decidido
  - type/adr
size_lines: 30
---

# ADR-071 — Playwright workspace isolation: email unique por worker

**Status:** Decidido • **Data:** 2026-04-15 • **Contexto da task:** F6.5F.6

**Contexto:** Playwright roda workers paralelos por default. Em E2E que faz registro de users (golden path, onboarding), 2 workers paralelos criando `e2e@test.com` causa race 409. Duas opções de isolation:

1. **Pool de workspaces pré-criadas:** seed 10 users/workspaces antes dos tests, workers sacam da pool + devolvem.
2. **Email unique por worker:** cada worker usa `e2e-w${parallelIndex}-${STAMP}@test.com`.

**Alternativas consideradas:**
- (A) Pool pré-criada — complexidade de setup (seed + cleanup), eficiente para testes longos mas overkill para smoke
- (B) **[escolhida]** Email unique por worker — helper `userForWorker(info)` gera email derivado de `parallelIndex` + `STAMP`. Cada worker opera em seu próprio "workspace fresco" sem coordenação
- (C) `fullyParallel: false` — serializa tests, mata paralelização

**Decisão:** Abordagem (B). Já implementada em `frontend/tests/e2e/helpers/auth.ts::userForWorker()` no Bootstrap. Workers NÃO compartilham state; cada um registra user novo por run.

**Cleanup:** users criados ficam no DB. Estratégia:
- **CI:** DB PG service é efêmero (spun up por run) → sem cleanup necessário
- **Local:** users acumulam em `mathoms.db`; documented em `TESTING.md` que dev pode dar `./scripts/test_backend_up.sh --reset` para zerar

**Consequências:**
- ✅ Zero coordenação entre workers — paralelização total
- ✅ Simples (3 linhas de código no helper)
- ✅ Cada test é hermético — falha de um worker não afeta outro
- ⚠️ DB local acumula users — reset manual quando ficar pesado
- ❌ Não exercita "user com dados pré-existentes" — esses cenários cobertos em integration tests (factories backend)

**Implementação:** já feita em Bootstrap. Esta ADR documenta a decisão para future-me não reabrir.
