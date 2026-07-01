---
id: A22.l2
type: lane
title: "Validação em 3 camadas (schema → invariante → 7 red lines hard-block)"
sprint: A22
plan: PLAN-launch-trust
status: shipped
priority: P0
branch_slug: a22-l2-validacao-3-camadas-red-lines
depends_on:
  - "[[A22.l1]]"
parallel_with: []
tags:
  - type/lane
  - sprint/a22
  - status/shipped
  - priority/p0
  - area/llm
---

# A22.l2 — Validação em 3 camadas + 7 red lines hard-block

> **Plano:** [[PLAN-launch-trust]] · Frente 3 (F3-O1) · **gate de KR7 (completa)**.
> Depende de [[A22.l1]] (harness + fixtures). **ADR Proposto antes do PR.**

## Objetivo

Endurecer o output do Parecer com validação em 3 camadas; violação de red line
→ Parecer rejeitado → fallback `needs_review` ([[A22.l3]]).

## Escopo — 3 camadas

1. **Schema** — Pydantic/Instructor `additionalProperties:false` + hard caps no
   `parecer_planejador.schema.json` (v1.0).
2. **Invariantes de domínio** — não recomenda alavancagem acima do threshold,
   não promete retorno, etc. (co-review `financial-planner`).
3. **7 red lines (hard-block):**
   1. Não promete/garante retorno futuro.
   2. Não recomenda alavancagem acima do threshold de domínio.
   3. Não recomenda zerar reserva de emergência.
   4. Não dá conselho fiscal específico sem disclaimer.
   5. Não inventa número fora do E5 (toda cifra rastreável ao input).
   6. Não recomenda produto financeiro nominal específico.
   7. Não contradiz invariante de domínio já calculado (IF, alocação-alvo).

## Critério de aceite

- 7/7 red lines disparam em teste contra fixtures de [[A22.l1]] (≥1 fixture
  adversarial por red line).
- Schema do Parecer com `additionalProperties:false` aplicado.
- Falha de validação → fallback `needs_review` (contrato com [[A22.l3]]).

## Notas

- Owner: `prompt-engineer` + `financial-planner` (co-review das red lines —
  são regra de domínio, invocar ao abrir a lane).
- **ADR Proposto** (escopo arquitetural: 7 red lines como invariante de domínio
  + boundary schema). Federa F3-O1 do plano dono.
