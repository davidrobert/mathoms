---
id: ADR-172
type: adr
title: "Stuck-runs detector via heartbeat + Celery beat"
status: Proposto
date: "2026-05-06"
relates_to: ["[[ADR-031]]", "[[ADR-119]]", "[[ADR-111]]"]
supersedes: []
superseded_by: []
aliases: ["ADR 172"]
tags:
  - area/backend
  - area/persistence
  - area/pipeline
  - status/proposto
  - type/adr
size_lines: 33
---

# ADR-172 — Stuck-runs detector via heartbeat + Celery beat

**Status:** Proposto • **Data:** 2026-05-06 • **Relaciona** [ADR-031](#adr-031--redis-para-queue--pubsub), [ADR-119](#adr-119--contrato-livestep-para-progresso-de-etapas-do-pipeline), [ADR-111](#adr-111--stateless-rigoroso-padrão-e-gate-empírico-a6f6). **Origem:** SR-007 (W2-T04).

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

**Implementação:** lane W2-T04. Vira `Decidido (W2-T04)` no merge.

**Referências:** [plan/PLATFORM_REVIEW/_README.md §W2-T04](plan/PLATFORM_REVIEW/_README.md), finding SR-007.
