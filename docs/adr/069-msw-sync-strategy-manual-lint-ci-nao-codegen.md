---
id: ADR-069
type: adr
title: "MSW sync strategy: manual + lint CI (não codegen)"
status: Decidido
date: "2026-04-15"
relates_to: []
supersedes: []
superseded_by: []
aliases: ["ADR 069"]
tags:
  - area/backend
  - area/testing
  - status/decidido
  - type/adr
size_lines: 29
---

# ADR-069 — MSW sync strategy: manual + lint CI (não codegen)

**Status:** Decidido • **Data:** 2026-04-15 • **Contexto da task:** F6.5F.5

**Contexto:** `frontend/tests/mocks/handlers.ts` define 50+ endpoints MSW que espelham `lib/api.ts`. Duas estratégias possíveis para manter sync com backend:

1. **Codegen via `openapi-typescript`:** baixar `openapi.json` do backend → gerar types + validar shapes dos handlers.
2. **Manual + lint CI:** handlers escritos à mão, contract test (6.5D.10) garante drift zero.

**Alternativas consideradas:**
- (A) Codegen completo → MSW handlers re-gerados a partir do OpenAPI + mocks auto-derivados. Custoso: requer adapter entre tipos OpenAPI e `HttpResponse.json()`, difícil testar cenários de erro customizados.
- (B) **[escolhida]** Manual + lint CI — devs escrevem handlers usando `lib/api.ts` types. Lint rodado em CI compara endpoints declarados em `handlers.ts` vs `openapi.json` do backend. Falha se há drift.
- (C) Nenhum mecanismo — confiar em reviews. Não-escalável com 50+ endpoints.

**Decisão:** Abordagem (B). `frontend/scripts/msw-lint.mjs` (scaffold inicial) lista URLs em `handlers.ts` (via AST parse de `http.<method>("/api/...")`) e diff contra `openapi.json` paths. Falha em endpoints backend sem handler correspondente OU handlers com URL que não existe no OpenAPI.

Integração com 6.5D.10 (contract test types) = complementar: aquele valida types, este valida URLs.

**Consequências:**
- ✅ Handlers escritos manualmente são leves (response body inline, fácil variar em tests)
- ✅ Cenários de erro (401, 422, 500) modelados naturalmente — codegen teria dificuldade
- ✅ Lint CI cobre "drift" — novo endpoint no backend sem handler → CI falha
- ⚠️ Primeiro run do lint precisa de baseline (lista de endpoints já presentes)
- ⚠️ Depende de backend estar UP para baixar `openapi.json` (ou pre-commit snapshot)
- ❌ Sem auto-sincronização — dev precisa atualizar `handlers.ts` ao adicionar endpoint

**Implementação:** scaffold em `frontend/scripts/msw-lint.mjs` (a criar, similar a `contract-check.mjs`). Ativar em CI após primeiro baseline.
