---
id: ADR-172
type: adr
title: "Stuck-runs detector via heartbeat + Celery beat"
status: Decidido
phase: Sprint A11.W2
date: "2026-05-06"
relates_to: ["[[ADR-031]]", "[[ADR-119]]", "[[ADR-111]]"]
supersedes: []
superseded_by: []
aliases: ["ADR 172"]
tags:
  - area/backend
  - area/persistence
  - area/pipeline
  - status/decidido
  - type/adr
size_lines: 51
---

# ADR-172 — Stuck-runs detector via heartbeat + Celery beat

**Status:** Decidido (Sprint A11.W2) • **Data:** 2026-05-06 • **Relaciona** [ADR-031](#adr-031--redis-para-queue--pubsub), [ADR-119](#adr-119--contrato-livestep-para-progresso-de-etapas-do-pipeline), [ADR-111](#adr-111--stateless-rigoroso-padrão-e-gate-empírico-a6f6). **Origem:** SR-007 (W2-T04).

**Contexto:** PipelineRun pode ficar "running" indefinidamente se o worker Celery morre (OOM, deploy, kill -9). Hoje não há detector — UI mostra "processando" eternamente, usuário não tem feedback, métricas inflam falso-positivo. ADR-119 (LiveStep) cobre progresso intra-stage mas não captura worker-death entre stages.

**Alternativas avaliadas:**

1. **Confiar em Celery `task_acks_late + visibility_timeout`** — funciona para retry, mas TTL long (default Mathoms 1h) e não atualiza UI. Rejeitada como solução única.
2. **Healthcheck via Redis SET NX por run** — adiciona estado externo; complica concurrency. Rejeitada por ADR-111 (preferimos DB como source-of-truth de estado durável).
3. **Coluna `last_heartbeat_at` em pipeline_runs + beat task scanning (escolhida)** — heartbeat barato (UPDATE simples), DB já é fonte de verdade, beat task é stateless.

**Decisão:** Adotar (3).

- **Migration:** `ALTER TABLE pipeline_runs ADD COLUMN last_heartbeat_at TIMESTAMP NULL`.
- **Stage start:** `UPDATE pipeline_runs SET last_heartbeat_at = NOW()` antes de executar e a cada checkpoint significativo (≥30s).
- **Beat task `fin.detect_stuck_runs`** roda a cada 5 min. Marca runs com `status='running' AND last_heartbeat_at < NOW() - INTERVAL 15 minutes` como `failed` com `failure_reason='heartbeat_timeout'`.
- **Notification + métrica `mathoms.pipeline.stuck_runs_detected`** disparada por run abandonada.
- **UI:** consome `failure_reason` e mostra mensagem honesta ("worker travou — clique em Reprocessar").

**Consequências:**

- ✅ Falha visível a usuário em ≤20 min worst-case (5 min beat + 15 min threshold).
- ✅ Métricas de SLO confiáveis — runs órfãs não distorcem `runs_in_progress`.
- ✅ Runbook trivial (just retry).
- ⚠️ Threshold 15 min é heurístico; pipeline genuinamente lento (extract LLM 5+ min) precisa de checkpoint intra-stage. Mitigação: stages LLM já chamam `update_progress` que atualiza heartbeat.
- ❌ Não detecta falsos-running — race entre worker hung + heartbeat update agendado em outra task. Aceito; coverage > 95% dos cenários reais.

**Implementação:** lane W2-T04 — entregue 2026-05-20.

**Closure (Sprint A11.W2):**

- Migration `adr172heartbeat_pipeline_runs_heartbeat`: 2 colunas + partial index `WHERE status='running'` + backfill defensivo (`UPDATE … SET last_heartbeat_at = started_at WHERE status='running'`).
- Write-path: `_mark_run_started` + `_record_stage_running` em [backend/app/tasks/pipeline_task.py](../../backend/app/tasks/pipeline_task.py).
- Beat task `fin.detect_stuck_runs` em [backend/app/tasks/periodic_tasks.py](../../backend/app/tasks/periodic_tasks.py) com UPDATE atômico (race-safe contra stage completion).
- Threshold configurável via `MATHOMS_STUCK_RUN_THRESHOLD_MINUTES` (default 15min); beat freq 300s.
- Vocabulário aberto de `failure_reason` em [backend/app/services/pipeline_failure_reasons.py](../../backend/app/services/pipeline/pipeline_failure_reasons.py) — começa com `heartbeat_timeout`, sem ENUM SQL.
- Log estruturado `mathoms.pipeline.stuck_run_detected` (via `MathomsJsonFormatter`).

**Referências:** [archive/PLATFORM_REVIEW_PLAN-2026-07-08.md §W2-T04](../archive/PLATFORM_REVIEW_PLAN-2026-07-08.md), finding SR-007.
