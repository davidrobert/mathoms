---
id: ADR-077
type: adr
title: "Pipeline adapter como contrato de cutover (CLI → Web)"
status: Decidido
phase: "F8.4"
date: "2026-04-15"
relates_to: []
supersedes: ["[[ADR-075]]"]
superseded_by: ["[[ADR-180]]"]
aliases: ["ADR 077"]
tags:
  - area/multitenancy
  - area/pipeline
  - status/decidido
  - type/adr
size_lines: 39
---

# ADR-077 — Pipeline adapter como contrato de cutover (CLI → Web)

**Status:** Decidido (F8.4) • **Data:** 2026-04-15

> **Nota (2026-05-07):** ✅ Fechado por
> [ADR-180](#adr-180--goalsjson-cutover-final-via-stageconfigconfig_store-extendido)
> (Sprint A10.6) e
> [ADR-181](#adr-181--goalsjson-removido-de-_archive-e-adicionado-a-devcheck_forbidden_pathspy)
> (Sprint A10.8). Checkbox "Contrato de cutover" marcado. Sprint A10
> entregou os 22 campos do `goals.json` em destinos canônicos (DB
> aggregates, rules-as-code, frontend estático ou deletados).

**Contexto:** As 4 fases anteriores (F8.0–F8.3) criaram entidades `Goal`, `Task`, `TaskSuggestion`, `TaskAttachment`, `FeatureFlag` no DB, endpoints REST, UI completa e testes. O pipeline legado (E5, E5.N, E6) continua lendo de `config/goals.json` e `config/tarefas.md`. O cutover precisa de uma ponte que permita ao pipeline operar via DB sem reescrevê-lo. Esta ADR formaliza o contrato dessa ponte.

**Decisão:**
1. **`backend/app/services/pipeline/pipeline_adapter.py`** é a fachada única entre pipeline e DB. Expõe 3 pares de funções (sync + async):
   - `build_goals_payload` → dict compatível com `goals.json`
   - `build_tasks_payload` → dict compatível com E5 `tarefas[]`
   - `build_tarefas_md` → string markdown compatível com `config/tarefas.md`
2. **Worker beat** (`backend/app/tasks/periodic_tasks.py`) roda `scan_all_deadlines` diariamente via Celery beat schedule — substitui a necessidade de cron externo.
3. **Feature flags** (`FeatureFlag` + `feature_flags_service.py`) controlam rollout por workspace: `tasks_v2_enabled`, `task_attachments_enabled`, `report_tasks_snapshot_enabled`, `task_deadline_notifications_enabled`.
4. **Snapshot automático** (ADR-074 §F8.3): `pipeline_task._create_report_from_output` chama `build_snapshot_sync` — relatórios novos nascem com foto imutável das tasks.

**Contrato de cutover** — a remoção de `config/goals.json` e `config/tarefas.md` do repo acontece quando:
- [x] O adapter cobre 100% dos campos lidos pelo E5/E5.N/E6 (seção `independencia_financeira` migrada em F8.1; `aportes`, `alocacao_alvo`, `dolarizacao` types adicionados em F8.4; restante de `goals.json` consolidado em Sprint A10 via `Decision`/`Risk` aggregates, rules-as-code (ADR-177), `Workspace.business_profile_json`, ou deleção de dead-data ADR-168 — checkbox fechado por ADR-180 (A10.6) + ADR-181 (A10.8) em 2026-05-07)
- [ ] Feature flag `tasks_v2_enabled` default ON para todas as workspaces
- [ ] Pipeline roda ciclo completo E0→E7 consumindo adapter (não arquivo) sem regressão
- [ ] Backup dos Grupo A (`_archive/pre-f8-cutover/`) + tag git

**Consequências:**
- ✅ Pipeline não precisa ser reescrito — consome adapter com mesmo contrato
- ✅ Cutover reversível via feature flag OFF (fallback para arquivo legado)
- ✅ Beat schedule descentraliza notificações — zero dependência de humano rodar scan
- ⚠️ Período de dual-source (DB + arquivo) até cobertura de 100% dos campos — aceito, mitigado pelo `_adapter_version` field que permite detectar payloads vindos do adapter vs. arquivo
- ❌ Scripts CLI (`scripts/e*.py`) ficam no repo como reference mesmo após cutover — remoção só em F9+ quando houver confiança de que a UI é autossuficiente

**Supersedes:** [ADR-075](#adr-075--cutover-cli--web-estratégia-de-transição-faseada-com-adapters) — esta ADR implementa e detalha o contrato declarado na 075.
