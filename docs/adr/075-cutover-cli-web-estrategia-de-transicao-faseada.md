---
id: ADR-075
type: adr
title: "Cutover CLI → Web: estratégia de transição faseada com adapters"
status: Decidido
phase: "F8"
date: "2026-04-15"
relates_to: []
supersedes: ["[[ADR-013]]"]
superseded_by: []
aliases: ["ADR 075"]
tags:
  - area/multitenancy
  - area/persistence
  - area/pipeline
  - status/decidido
  - type/adr
size_lines: 55
---

# ADR-075 — Cutover CLI → Web: estratégia de transição faseada com adapters

**Status:** Decidido (F8) • **Data:** 2026-04-15 • **Contexto da task:** F8.0-F8.4 — migração completa

**Contexto:** O pipeline original (E0-E7) foi construído como CLI determinístico + etapas LLM manuais — scripts Python em `scripts/` que leem `config/*.json`, `config/tarefas.md`, `data/` e escrevem em `processed/` e `output/`. A partir de F1 o produto incorporou backend + frontend, mas o pipeline determinístico continua rodando via worker Celery que envelopa os scripts CLI ([ADR-013](#adr-013--wrap-dont-rewrite-pattern) — "wrap, don't rewrite"). **A decisão confirmada pelo usuário em F8 é: a app web substitui o pipeline CLI**. Isso não significa reescrever tudo de uma vez — significa que o CLI deixa de ser interface suportada e a fonte de verdade migra `config/*.json` → DB.

O risco principal: quebrar o pipeline durante a transição e perder capacidade de gerar relatórios antes que a UI seja equivalente. Mitigação via **adapters**: scripts continuam rodando com I/O preservado, mas leem do DB em vez de arquivos.

**Alternativas consideradas:**
- (A) **Big-bang rewrite** — reescreve E5, E5.N, E6 em F8.4 e desliga CLI.
  - ❌ Rejeitada: F6.5 acabou de consolidar 438 testes contra o pipeline atual. Reescrever antes de substituir integralmente a UI perde a rede de segurança.
- (B) **Manter dual-source indefinidamente** — DB como source of truth para UI, `config/*.json` para pipeline.
  - ❌ Rejeitada: dual-write é origem clássica de inconsistência. Aceitável como fase, não como destino.
- (C) **Adapter pattern faseado + remoção gradual de arquivos do repo** — DB passa a ser fonte única; scripts consultam DB via `pipeline_adapter`; arquivos de config de usuário são removidos do repo fase por fase.
  - ✅ **Escolhida**: preserva robustez do pipeline atual, migra source of truth uma entidade por vez, e termina com `config/` contendo apenas seeds/templates de produto (institutions, categorization keywords) — não mais dados de usuário.

**Decisão:**
1. **Contrato de adapter** — `backend/app/services/pipeline_adapter.py` é a única fachada entre pipeline scripts e DB. Funções:
   - `build_goals_payload(workspace_id) -> dict` (replica estrutura de `goals.json`)
   - `build_tasks_payload(workspace_id) -> dict` (replica `tarefas[]` do JSON E5)
   - `build_tarefas_md(workspace_id) -> str` (formato markdown, compat legado)
   - `build_family_members_payload(workspace_id) -> dict` (de `family_members.json`)
   - ...outras conforme entidades migrem
2. **Classificação dos artefatos de `config/`** em 3 grupos:
   - **Grupo A — Dados do usuário** (migram para DB): `goals.json`, `tarefas.md`, `family_members.json`, `cenarios.json`, `decisions.md`. Removidos do repo ao final de F8.4.
   - **Grupo B — Seeds/templates de produto** (permanecem no repo): `institutions.json` (padrões de banco), `categorization.json` (keywords default), `parametros_fiscais.json` (alíquotas), `localization.json`, `taxas.json`, `scoring.json`. Carregados como seed no primeiro acesso do workspace; usuário pode editar cópia via `config_blob`.
   - **Grupo C — Documentação** (permanecem): `definitions.md`, `methodology.md`, `source_hierarchy.md`, `regras_composicao_patrimonial.md`, `report_layout.yaml`, `report_spec.md`. Nota: `manual_operacao.md` foi arquivado em `_archive/manual_operacao_v6.1.md` (versão agora em `pipeline.json::report_version`). `decisions.md` listado em Grupo A para migração ao DB.
3. **Ordem de migração** (escolhida para minimizar risco):
   - **F8.1**: `goals.json` (parcial — só `independencia_financeira`) + adapter para resto
   - **F8.2**: `tarefas.md` completo
   - **F8.3**: integrações profundas (Task↔Transaction↔Goal)
   - **F8.4**: migração completa do resto do `goals.json` (aportes, alocação, riscos), `family_members.json`, `cenarios.json`, `decisions.md` — E5 passa a ler tudo do DB, remoção dos arquivos de Grupo A do repo.
4. **Feature flags** por módulo — `goals_v2_enabled`, `tasks_v2_enabled`, `report_snapshot_v2_enabled`, todas workspace-level. Durante transição, flag OFF = pipeline usa arquivo legado; flag ON = pipeline usa adapter. Default ON no workspace dogfood inicial assim que módulo entrega; default ON para todos em F8.4.
5. **Scripts CLI desabilitados em produção** — a partir de F8.4, `scripts/e*.py` são executáveis **apenas** via worker (import como módulo, não invocação CLI). Mantidos no repo como implementação de reference; `README.md` documenta que a interface suportada é a UI. Remoção total dos scripts fica como débito F9+ quando for seguro.
6. **Regressão blindada** — cada fase roda o ciclo completo E0→E7 antes/depois em workspace de teste e faz diff dos artefatos (tolerância: só diferença em timestamps). Falha de paridade = rollback automático.
7. **Backup dos Grupo A antes da remoção** — último snapshot pre-F8.4 vai para `_archive/pre-f8-cutover-2026-XX-XX/` com tag git, para referência histórica e auditoria.

**Consequências:**
- ✅ Pipeline atual segue funcionando a cada fase — risco de quebra limitado à entidade que migra
- ✅ Rollback de uma fase é reversão de flag, não de deploy
- ✅ `config/` termina enxuto (só produto), não mais mistura dados de usuário
- ✅ Claro para desenvolvedores: fontes de verdade explícitas por grupo
- ⚠️ Complexidade adicional do adapter durante transição — aceito; código isolado, removível
- ⚠️ Testes duplicados (pipeline lendo arquivo vs. pipeline lendo DB) durante transição — removidos ao fim de F8.4
- ❌ Advanced pipeline features novas (ex: goal recalculation on-demand disparado por UI) ficam esperando F8.4 — aceito
- ❌ CLI permanece tecnicamente executável pós-F8.4 (scripts não removidos), mas sem suporte — aceito

**Supersedes parcial:** [ADR-013 "Wrap, don't rewrite"](#adr-013--wrap-dont-rewrite-pattern) — a filosofia original era wrap indefinido. F8 formaliza migração eventual dos wraps em adapters DB, com remoção dos arquivos de config de usuário do repo. O padrão "wrap" continua válido para scripts que não migram (E0 route, E2 parsers).

**Implementação:**
- F8.0: contrato e stubs do adapter, CI test que valida assinatura de funções do adapter
- F8.1+: cada fase implementa as funções correspondentes e migra scripts para usá-las
- F8.4: checklist de cutover (backup → remoção de arquivos Grupo A → desabilitar entradas CLI do Makefile/documentação → atualizar docs relevantes)
