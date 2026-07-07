---
id: A33.l5
type: lane
title: "Nightly drift do extract_with_llm: Celery beat + fixtures sintéticas + auto-alerta (ADR-307 F2)"
sprint: A33
plan: PLAN-platform-review
status: planned
priority: P2
branch_slug: a33-l5-nightly-drift-extractllm
adrs: ["[[ADR-307]]"]
depends_on: []
parallel_with: ["[[A33.l4]]", "[[A33.l6]]"]
tags:
  - type/lane
  - sprint/a33
  - status/planned
  - priority/p2
  - area/llm
  - area/observability
---

# A33.l5 — `nightly-drift-extractllm` (follow-up F2 da [[ADR-307]])

## Problema

[[ADR-307]] (Decidido 2026-07-06, #796/#797) entregou cache + hooks
MLOps universais, e registrou como follow-up F2: "extração ganha job
nightly próprio: 3-5 casos sintéticos, 1 trial, assertions estruturais,
auto-issue". Sem o job, drift de provider no `extract_with_llm` só
aparece quando um documento real quebra — em produção.

## Escopo

1. Task Celery beat nightly (`backend/app/tasks/` — nome específico,
   ex. `detect_extract_llm_drift`), agenda fora de horário de pico.
2. 3-5 fixtures sintéticas PII-zero (padrão
   `tests/fixtures/pipeline_golden/`), 1 trial por fixture.
3. Assertions **estruturais** (shape/campos/tipos do output vs. schema),
   não bit-exact — drift de temperatura ≠ drift de contrato.
4. Falha → log `ERROR` estruturado namespace `mathoms.llm` + registro
   consultável (padrão de alerta existente do backend); métrica de drift
   emitida.
5. Invariante preservada: **CI de PR nunca chama Anthropic real** — o
   job roda no ambiente Celery (dev/prod, key já existente no env do
   backend); nada de secret novo.

## Critérios de aceite

1. Job agendado no beat com teste de agenda + teste unitário do corpo
   com fake LLM (`tests/fakes/`).
2. 1ª execução real registrada em `llm_call_log` (KR5) — disparo manual
   da task pelo agente via ambiente dev, sem ação do owner.
3. Custo por execução documentado no corpo da task (fixtures pequenas;
   ordem de centavos/noite — sob o cap [[ADR-173]]).
4. PR mergeado em `main` (squash) com CI verde.
