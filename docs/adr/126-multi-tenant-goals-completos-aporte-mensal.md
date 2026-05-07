---
id: ADR-126
type: adr
title: "Multi-tenant Goals completos (APORTE_MENSAL, DOLARIZACAO, ALOCACAO_ALVO)"
status: Decidido
phase: "F8.5"
date: "2026-04-16"
relates_to: []
supersedes: []
superseded_by: []
aliases: ["ADR 126"]
tags:
  - type/adr
  - status/decidido
size_lines: 43
---

# ADR-126 — Multi-tenant Goals completos (APORTE_MENSAL, DOLARIZACAO, ALOCACAO_ALVO)

> Renumerado de ADR-079 (duplicata) em 2026-04-24 para resolver colisão com
> ADR-079 "Content-first classification no upload web" (linha ~1510).
> O conteúdo abaixo é o original; referências externas ao antigo "ADR-079
> (multi-tenant goals)" devem migrar para ADR-126.

**Status:** Decidido (F8.5) • **Data:** 2026-04-16

**Contexto:**
Após F8.1 (ADR-073), apenas `INDEPENDENCIA_FINANCEIRA` tinha API + UI; os outros 3 tipos declarados em `VALID_GOAL_TYPES` ficavam como débito. O `config/goals.json` foi arquivado no cutover F8.4, mas sem UI para substituí-lo, workspaces sem seed travavam o pipeline com `ValueError: Estratégia de aportes não encontrada em goals.json` no E6. Diagnóstico: (1) E6 violava fail-safe defaults (duas funções com `raise` em vez de fallback); (2) não havia caminho multi-tenant para o usuário configurar aportes/dolarização/alocação via UI.

**Decisão:**
1. **Resiliência do E6**: `build_estrategia_aporte` e `_build_top5_decisoes_fallback` em `scripts/e6_render.py` passam a degradar graciosamente (warning + struct mínima) em vez de `raise ValueError`, alinhando com o padrão do resto do arquivo (`_build_riscos_fallback`, etc.). Banner CTA é injetado no HTML quando goals estão vazios.
2. **Backend F8.5** — API completa para os 3 tipos restantes, seguindo o padrão IF literalmente:
   - Schemas Pydantic em `backend/app/schemas/goal.py` (validadores: soma distribuição == meta, soma pcts alocação == 100)
   - `_GoalResponseBase` compartilhada por todos os Response types
   - Service funcs puras: `compute_aporte_derived`, `compute_dolar_derived`, `compute_alocacao_derived`
   - `create_goal_version` genérica (substitui duplicação de 3x `create_*_goal_version`)
   - `get_current_goal_typed` / `get_goal_history_typed` via mapa `_GOAL_TYPE_CLASSES`
   - 12 endpoints: POST compute, GET current, GET history, PUT upsert (por tipo)
3. **Frontend F8.5**:
   - 3 edit pages + 3 wizards em `frontend/src/app/(app)/plano/{aportes,dolarizacao,alocacao}/`
   - Types + 12 funções API client em `lib/api.ts`
   - `/plano` refatorada para dashboard multi-goal (grid 2×2 status cards) + banner CTA quando 0 goals configurados
4. **DOLARIZACAO usa câmbio hardcoded (`DEFAULT_CAMBIO_BRL_USD = 5.70`)** como MVP — override via `cambio_brl_usd` no compute request. Integração com API externa fica como débito futuro.
5. **ALOCACAO_ALVO valida soma=100** tanto no Pydantic (`model_validator`) quanto no endpoint (`valido` flag no compute response).

**Consequências:**
- ✅ Qualquer workspace pode configurar todas as 4 metas via UI sem depender de arquivo pré-seedado
- ✅ Pipeline nunca mais crasha por goals ausentes — degrada graciosamente com warning + banner CTA
- ✅ Refactor para generic helpers (`create_goal_version`, `get_current_goal_typed`) evita 3x duplicação mantendo backward compat com IF
- ✅ Fluxo end-to-end: UI → DB → adapter → `goals.json` materializado → E5/E6 → relatório
- ⚠️ Câmbio hardcoded em DOLARIZACAO fica desatualizado — aceito; override manual + débito futuro
- ⚠️ Validação de distribuição no APORTE é strict (soma == meta ±0.01) — usuário não pode salvar parcial
- ❌ PLANNING_CONTEXT (23 seções legadas) ainda sem UI — goals restantes (fase_f1f2, seguros, etc.) são seedados só via `seed_goals_full_ferreira_campos.py` ou permanecem vazios

**Arquivos críticos:**
- Backend: `backend/app/schemas/goal.py`, `backend/app/services/goal_service.py`, `backend/app/api/goals.py`
- Frontend: `frontend/src/lib/api.ts`, `frontend/src/app/(app)/plano/page.tsx`, `frontend/src/app/(app)/plano/{aportes,dolarizacao,alocacao}/{page,wizard/page}.tsx` (7 arquivos novos/refatorados)
- Pipeline: `scripts/e6_render.py` (resiliência + banner CTA)
