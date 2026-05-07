---
id: ADR-073
type: adr
title: "Goals como entidade versionada (não config estático)"
status: Decidido
phase: "F8"
date: "2026-04-15"
relates_to: []
supersedes: []
superseded_by: []
aliases: ["ADR 073"]
tags:
  - type/adr
  - status/decidido
size_lines: 43
---

# ADR-073 — Goals como entidade versionada (não config estático)

**Status:** Decidido (F8) • **Data:** 2026-04-15 • **Contexto da task:** F8.1 — Metas IF

**Contexto:** Hoje o objetivo de Independência Financeira (IF) vive em [config/goals.json:19-27](config/goals.json:19) como `if_meta: 7200000.0` — um número digitado à mão, sem derivação matemática, sem histórico de mudanças, sem audit de quem alterou. No modelo multi-família, cada workspace precisa ter sua meta própria, editável por UI, e é essencial preservar **trajetória** (qual era a meta em jan/2025 vs. abr/2026) para gráficos de progresso e comparativos "antes/depois". O valor tampouco deve ser digitado diretamente: é derivado de `renda_passiva_mensal × 12 / trs_pct` — e o usuário pensa em termos de renda desejada, não de patrimônio-alvo.

**Alternativas consideradas:**
- (A) **Reusar `ConfigBlob`** (modelo existente que armazena JSON arbitrário por workspace — padrão do [ADR-020](#adr-020--materializar-config-em-disco)).
  - ❌ Rejeitada: não versiona por default, sem semântica de "vigência", e mistura goals (dado crítico com narrativa no produto) com configs operacionais (keywords, thresholds). Goal merece tipo forte.
- (B) **Model único `Goal` com JSONB `params_json` + `derived_json`** — `type` discrimina IF, Aporte Mensal, Dolarização, etc.
  - ✅ **Escolhida**: flexível para tipos variados (goals.json atual tem 10+ "seções" de meta), versiona com `effective_from`, valida por tipo via JSON Schema.
- (C) **Model por tipo (`IFGoal`, `MonthlyContributionGoal`, ...)** — rigor máximo de tipagem.
  - ❌ Rejeitada: cada novo tipo de goal exige migration; a variação acontece muito cedo no produto para cristalizar em tabelas separadas.
- (D) **Digitar `if_meta` diretamente no formulário** — simpler.
  - ❌ Rejeitada: usuário pensa em "quanto quero receber por mês?", não "qual meu patrimônio-alvo?". Forçar o cálculo matemático explícito é pedagógico e elimina inconsistências.

**Decisão:**
1. **Tabela `goals`** com colunas: `id (UUID)`, `workspace_id (FK)`, `type (Enum)`, `params_json (JSONB)`, `derived_json (JSONB)`, `effective_from (Date)`, `effective_to (Date|NULL)`, `created_by (FK user)`, `notes (text)`, `created_at`, `updated_at`.
2. **Versionamento por append-only** — edição cria novo registro com `effective_from = hoje` e fecha o anterior com `effective_to = ontem`. Registro vigente é único por `(workspace_id, type)` e tem `effective_to IS NULL`.
3. **Derivação server-side** — `goal_service.compute_if_derived(inputs: dict) -> dict` é função pura, testada, e é **a única fonte** do cálculo. Frontend chama `POST /goals/if/compute` para preview live; pipeline chama a mesma função.
4. **Schema canônico por tipo** — `config/schemas/goal.if.schema.json` (criar) define `params_json.inputs.{renda_passiva_mensal_brl, trs_pct, retorno_real_anual_pct, horizonte_anos, taxa_retirada_conservadora_pct}` e `derived.{if_meta_brl, aporte_necessario_mensal_brl, if_meta_conservadora_brl}`. Backend valida write, frontend gera tipos TS via codegen (OpenAPI).
5. **Tipos de goal implementados**: `INDEPENDENCIA_FINANCEIRA` em F8.1; `APORTE_MENSAL`, `DOLARIZACAO`, `ALOCACAO_ALVO` em F8.5 (ver ADR-126). `PLANNING_CONTEXT` cobre as 23 seções restantes do `goals.json` como blob genérico via adapter.
6. **Migração do `goals.json` de Ferreira Campos** — one-shot script em `backend/app/scripts/seed_if_goal_ferreira_campos.py` cria registro inicial para a workspace existente com `renda_passiva_mensal_brl=30000, trs_pct=5.0, retorno_real_anual_pct=6.0` → `derived.if_meta_brl=7200000` (paridade bit-a-bit com valor legado).
7. **Novos workspaces** — seed cria Goal template flag `is_template=true` com valores default (renda 20k/mês, trs 5%). UI do dashboard detecta a flag e força wizard antes de liberar outras funcionalidades.
8. **Pipeline (E5/E5.N)** — lê Goal vigente via `pipeline_adapter.build_goals_payload(workspace_id)` que retorna dict no formato atual de `goals.json` (campo `independencia_financeira`). Rest de `goals.json` (`aportes`, `fase_f1f2`, etc.) continua servido pelo adapter a partir de fontes legadas até F8.5.

**Consequências:**
- ✅ Histórico preservado — é possível mostrar "sua meta subiu 8% no último ano" e gerar gráfico de progresso real
- ✅ Derivação única — zero risco de UI mostrar 7.2M enquanto pipeline calcula 7.5M
- ✅ Validação por schema versionável (`meta_version`) — permite evoluir sem quebrar históricos
- ✅ Audit log natural via `created_by` + `effective_from`
- ⚠️ Migração dos outros "tipos de goal" (aportes, alocação alvo) fica como débito — durante transição, `goals.json` continua existindo como seed + override legado
- ❌ Não temos "rascunho" de goal (user editando sem commit) — aceito; wizard confirma antes de persistir

**Implementação inicial (F8.1):**
- `backend/app/models/goal.py` + Alembic migration
- `backend/app/services/goal_service.py` (`compute_if_derived`, `create_goal_version`, `get_current_goal`, `get_goal_history`)
- `backend/app/api/goals.py` com endpoints documentados no plano de execução
- `config/schemas/goal.if.schema.json`
- Testes unitários de `compute_if_derived` (10+ casos) + integração multi-workspace
- Script one-shot de seed para o workspace inicial (dogfood)
