---
id: A37.l12
type: lane
title: "Resiliência de execução: heartbeat in-stage (watchdog 15min) + idempotência de stage LLM em redelivery"
sprint: A37
status: planned
priority: P2
branch_slug: a37-l12-resiliencia-execucao
adrs: []
depends_on: []
tags:
  - type/lane
  - sprint/a37
  - status/planned
  - priority/p2
  - area/backend
  - area/infra
---

# A37.l12 — `resiliencia-execucao` (CTO-06 + EXEC-01)

## Problema (evidência verificada 2026-07-20 @ c61c1c29)

1. **CTO-06 — watchdog com margem fina:** `last_heartbeat_at` só é escrito em
   run-start e stage-start (`backend/app/tasks/pipeline_task.py:719,767` —
   únicos 2 pontos no repo); `detect_stuck_runs`
   (`backend/app/tasks/periodic_tasks.py`, threshold 15 min, beat 300s) flipa
   o run para `failed` + notifica o usuário + publica WS. No run auditado, o
   stage mais longo levou 12,2 min **ativos** (81% do threshold); nunca mordeu
   (85 runs sem `HEARTBEAT_TIMEOUT`), mas um stage LLM com muitos docs em
   produção excede 15 min com facilidade → run saudável marcado `failed`, com
   flip-flop possível quando o worker conclui depois.
2. **EXEC-01 — redelivery re-paga LLM:** no run auditado, o redelivery Celery
   (pós-sleep do host) re-executou `extract_members` já concluído → 2ª call
   LLM idêntica (~US$0,26 duplicado) e rows duplicadas em stage logs. Em
   produção, crash/restart de worker no meio do run re-paga stages LLM — não
   há guard de idempotência por stage concluído.

## Escopo

- Heartbeat **in-stage** inline no loop de documentos (DB write a cada N docs)
  — **sem** thread/timer no worker ([[ADR-111]] proíbe `threading`/`create_task`
  fora do Celery). Guard anti flip-flop via **UPDATE condicional atômico**
  (compare-and-set `... WHERE status=<esperado>`), nunca read-modify-write
  cross-worker.
- Idempotência de redelivery: antes de re-executar um stage, checar um
  **marcador de conclusão de stage** para o `(run_id, stage)` — não só "artifact
  existe", que não cobre redelivery mid-stage antes do write — e **pular** (ou
  reusar) em vez de re-chamar LLM; registrar `redelivered=true` na telemetria.

## Critério de aceite

- Teste (fake clock): stage simulado de 20 min com heartbeat in-stage → watchdog
  **não** flipa; sem batida → flipa (comportamento atual preservado p/ travas
  reais).
- Teste de regressão: redelivery de task com stage já concluído → zero call
  LLM nova (fake LLM client conta chamadas), artifacts inalterados.
- Sem violação de [[ADR-111]] (stateless): heartbeat via DB, nada in-memory.

## Risco

Médio: mexe no caminho quente do worker — cobrir com o teste de concorrência
multi-worker existente; rollout com threshold env-var para ajuste sem deploy.
