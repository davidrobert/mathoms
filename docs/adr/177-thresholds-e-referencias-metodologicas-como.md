---
id: ADR-177
type: adr
title: "Thresholds e referências metodológicas como código (rules-as-code consolidation `goals.json`)"
status: Decidido
phase: "Sprint A10.2"
date: "2026-05-06"
relates_to: []
supersedes: []
superseded_by: []
aliases: ["ADR 177"]
tags:
  - area/frontend
  - area/methodology
  - area/pipeline
  - methodology/auvp
  - methodology/cerbasi
  - methodology/perini
  - status/decidido
  - type/adr
size_lines: 44
---

# ADR-177 — Thresholds e referências metodológicas como código (rules-as-code consolidation `goals.json`)

**Status:** Decidido (Sprint A10.2) • **Data:** 2026-05-06 • **Data de decisão:** 2026-05-07 • **Aplica** [ADR-143](#adr-143--docsmethodology-é-rules-as-code-sprint-a76). **Origem:** Sprint A10 W0 — [archive/GOALS_JSON_CUTOVER_PLAN-2026-05-07.md §2.2 chaves U/M/O](archive/GOALS_JSON_CUTOVER_PLAN-2026-05-07.md).

**Contexto:** O `config/goals.json` (arquivado em F8.4 mas ainda materializado em runtime por [`pipeline_task.py::_materialize_adapter_configs`](../backend/app/tasks/pipeline_task.py:56)) carrega 22 chaves heterogêneas. Inventário decisional do plano canônico classificou 7 delas como **universais (U) / metodológicas (M) / operacionais (O)** — não variam por cliente, são thresholds ou referências de mercado. ADR-143 (Sprint A7.6) já estabeleceu doutrina: regras universais de produto vivem em **docstrings + constantes em módulos enforcers** + ADR canônica como rationale. JSON externo para esses valores é o anti-padrão exato que ADR-143 combate — vira mock-config-driven pois ninguém edita o arquivo em produção.

**Chaves no escopo:**

- `imoveis.yield_potencial_pct_min/max` (4-6% FII/imóvel BR — referência de mercado).
- `thresholds.imovel_pct_patrimonio_ideal: 50` (concentração imobiliária; convergente Perini passivo + AUVP).
- `thresholds.equity_pct_alvo_min/max` (range default por perfil; override por cliente cabe em Goal `ALOCACAO_ALVO` existente como `target_min_pct`/`target_max_pct` opcional).
- `simulacao.aporte_reduzido_fator: 0.66` (heurística "cônjuge 66%"; convergente Cerbasi renda dupla — já tem default no código).
- `stress_test_imovel_queda_pct: 20` (threshold metodológico stress test imobiliário).
- `dashboard.aporte_match_keywords` — **VIVO** em [`task_progress_service.py:63`](../backend/app/services/task_progress_service.py:63); migra para constante imutável `_APORTE_MATCH_KEYWORDS` no módulo.
- `referencias.{livros, ferramentas, contatos_templates}` (bibliografia/ferramentas/templates de perfil — frontend estático em página Sobre/Metodologia).
- `calendario_fallback[]` (template estático por horizonte; itens USA-only filtrados após ADR-168).

**Não-objetivo:** chaves cliente-específicas (`aportes`, `independencia_financeira`, `dolarizacao`, `alocacao_alvo` — já têm Goal type) ficam fora. `tetos_orcamentarios`, `viagens.teto_anual`, `tributario` também ficam fora (deletados em A10.1 ou migrados em A10.7).

**Decisão:** Migrar as 7 chaves para rules-as-code (constantes em módulos enforcers + docstring justificando a fonte) ou conteúdo estático no frontend (`/sobre`, `/metodologia`). Cada constante referenciada via `**Aplica** ADR-177` em docstring local. `goals.json` deixa de ser fonte para esses valores ao final da Sprint A10.

**Alternativas consideradas:**

1. **Manter `goals.json` como source of truth via `ConfigStore.get_methodology_thresholds()`** — perpetua mock-config-driven; ninguém edita em produção; ADR-143 já provou que o caminho é código + ADR.
2. **Tabela DB versionada por data (estilo `fiscal_parameters` ADR-135)** — overkill para 7 thresholds que não mudam por workspace nem por data fiscal. Custo de migration + repo + UI sem ganho concreto.
3. **Constantes em módulos + docstrings + ADR (escolhida)** — alinhada com ADR-143; zero infra; muda via PR + revisão; gates de PR já cobrem.

**Trade-offs explícitos:**

- **Ganho:** consolidação numa única doutrina (ADR-143); deleta 7 chaves do goals.json sem perder rastreabilidade; testes de regressão validam invariantes (ex.: `imovel_pct_patrimonio_ideal == 50` em test).
- **Custo:** mudar threshold exige PR (vs. edit em JSON). Aceito — esses valores **devem** passar por revisão; se vão para JSON acessível ao consultor, vira ADR e Goal type dedicado quando demanda materializar.
- **Risco:** pequeno. `aporte_match_keywords` é o único leitor vivo (já mapeado); demais não têm leitor após cleanup.

**Critério de aceite:**

- [ ] 7 chaves `imoveis.yield_potencial_pct_*`, `thresholds.imovel_pct_patrimonio_ideal`, `thresholds.equity_pct_alvo_*`, `simulacao.aporte_reduzido_fator`, `stress_test_imovel_queda_pct`, `dashboard.aporte_match_keywords`, `referencias.*`, `calendario_fallback[]` migradas — cada constante em módulo enforcer (backend/pipeline) ou static content frontend.
- [ ] `dashboard.aporte_match_keywords` em `task_progress_service.py` lido via `_APORTE_MATCH_KEYWORDS` constante imutável; nenhum `goals_cfg["dashboard"]["aporte_match_keywords"]` remanescente.
- [ ] `referencias.{livros, ferramentas, contatos_templates}` viraram conteúdo estático em `frontend/src/app/(public)/metodologia/page.tsx` (ou similar) — sem leitura de arquivo.
- [ ] Tests unitários afirmam invariantes: `IMOVEL_PCT_PATRIMONIO_IDEAL == 50`, `STRESS_TEST_IMOVEL_QUEDA_PCT == 20`, etc.
- [ ] `grep -r "goals_cfg\[\"thresholds\"\]\[\"imovel_pct" backend/ pipeline/` retorna zero.

**Plano de implementação:** [docs/archive/GOALS_JSON_CUTOVER_PLAN-2026-05-07.md §2.2](archive/GOALS_JSON_CUTOVER_PLAN-2026-05-07.md) (lane A10.2).
