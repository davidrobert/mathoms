---
id: A22.l4
type: lane
title: "Drift detection (3 sinais) + pin de model-snapshot"
sprint: A22
plan: PLAN-launch-trust
status: planned
priority: P1
branch_slug: a22-l4-drift-detection-model-pin
depends_on:
  - "[[A22.l1]]"
parallel_with: []
tags:
  - type/lane
  - sprint/a22
  - status/planned
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
