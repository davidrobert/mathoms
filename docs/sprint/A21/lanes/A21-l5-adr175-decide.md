---
id: A21.l5
type: lane
title: "Decidir ADR-175 (defesa de injeção LLM em camadas) Proposto→Decidido"
sprint: A21
plan: PLAN-launch-trust
status: shipped
priority: P0
branch_slug: a21-l5-adr175-decide
depends_on: []
parallel_with: []
adrs:
  - "[[ADR-175]]"
tags:
  - type/lane
  - sprint/a21
  - status/shipped
  - priority/p0
  - area/llm
  - area/seguranca
---

# A21.l5 — Decidir ADR-175 (defesa de injeção LLM)

> **Plano:** [[PLAN-launch-trust]] §F3-O3 (federada → [PLAN-platform-review](../../../archive/PLATFORM_REVIEW_PLAN-2026-07-08.md) W3-T05).
> **Gate (b) de F3** — parte 1 de 2.

## Contexto

[[ADR-175]] já existe como `Proposto` (criado em A11/W1-T06, PR #94), com a
defesa de injeção de **4 camadas** já desenhada (sanitization, system clause
`<USER_DOC>`, Pydantic strict via [[ADR-026]], adversarial fixtures). Falta
**decidir** — sem isso, W3-T05 (l6) não pode implementar, e o gate (b) de F3
fica fechado.

## Escopo

- Revisar a Proposto com `senior-cto` (decisão arquitetural) + `prompt-engineer`
  (Layer 2 system clause PT-BR, comportamento cross-provider, Layer 4 fixtures).
- Flippar [[ADR-175]] `Proposto → Decidido (Sprint A21 L5)`.
- Ajustar a Proposto se a revisão mudar a abordagem (ex.: telemetria
  `mathoms.llm.input_sanitized`).

## Critério de aceite

- [[ADR-175]] `Decidido` em `main`.
- Escopo de l6 confirmado por `prompt-engineer` antes do pickup de l6.

## Dependências

- **Sem deps** — pickup imediato no dia 1. XS (~30min de raciocínio + flip).
- Destrava l6.
