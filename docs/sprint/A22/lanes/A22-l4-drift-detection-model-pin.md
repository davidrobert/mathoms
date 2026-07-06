---
id: A22.l4
type: lane
title: "Drift detection (3 sinais) + pin de model-snapshot"
sprint: A22
plan: PLAN-launch-trust
status: shipped
priority: P1
branch_slug: a22-l4-drift-detection-model-pin
depends_on:
  - "[[A22.l1]]"
parallel_with: []
tags:
  - type/lane
  - sprint/a22
  - status/shipped
  - priority/p1
  - area/llm
---

# A22.l4 — Drift detection + pin de model-snapshot

> **Plano:** [[PLAN-launch-trust]] · Frente 3 (F3-O4) · **Should** (qualidade,
> não bloqueio). Depende de [[A22.l1]] (baseline de distribuição).

## Objetivo

Detectar drift do Parecer entre versões de prompt/model e pinar o snapshot do
model (não `latest`), usando a telemetria de prompt já em `main`.

## Escopo — 3 sinais

1. **Distribuição de confidence** — desvio vs. baseline dos goldens.
2. **Taxa de `needs_review`** — subida anômala.
3. **Δ tokens/custo** entre `PROMPT_VERSION` (gate [[ADR-233]]).

- Pin de model-snapshot (temperatura 0.3 + versão fixa, não `latest`).
- Consome `backend/app/models/llm_call_log.py` + `parecer_orchestrator.py`
  (telemetria já instrumentada).

## Critério de aceite

- 3/3 sinais emitindo em dogfood; pin de model aplicado.
- Sem novo gate de PR bloqueante (Should — observabilidade).

## Notas

- Owner: `prompt-engineer`.
- Estende telemetria existente (ADR-110 / ADR-233); sem ADR nova.
- Federa F3-O4 do plano dono. Escorrega para A23 sem bloquear o fechamento.

## Entrega (2026-07-06)

Shipped via `backend/app/services/parecer_drift_monitor.py` + hook fail-open
em `planner_review_persistence._safe_persist` (pós-commit). **5 sinais** (3 da
lane + 2 do co-design `prompt-engineer`): confidence Δ e needs_review Δ com
banda `max(floor, 2·SE)` e piso N=8 (honesto com N pequeno), tokens/custo Δ
±30%, duration p95 Δ ±40% (proxy de reask storm ADR-292/294), model swap sob
mesma prompt_version (warn N=1). Janela por `(prompt_version, model_name)`;
baseline relativo `prev_version` com skip de baseline ruidoso; contrato aberto
p/ `baseline_kind="golden"` quando [[A22.l1]] destravar. Pin: PARECER_MODEL já
era literal — travado por `tests/unit/pipeline/test_parecer_model_pin.py`.
Temp permanece 0.1 (ADR-202; o 0.3 da spec original não foi aplicado — mudança
de temperatura é decisão de prompt fora do escopo de observabilidade).
