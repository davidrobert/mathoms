---
id: A21.l6
type: lane
title: "W3-T05 — defesa de injeção LLM (4 camadas + adversarial fixtures + telemetria)"
sprint: A21
plan: PLAN-launch-trust
status: planned
priority: P0
branch_slug: a21-l6-prompt-injection-defense
depends_on:
  - "[[A21.l5]]"
parallel_with: []
adrs:
  - "[[ADR-175]]"
tags:
  - type/lane
  - sprint/a21
  - status/planned
  - priority/p0
  - area/llm
  - area/seguranca
---

# A21.l6 — W3-T05 defesa de injeção LLM (implementação)

> **Plano:** [[PLAN-launch-trust]] §F3-O3 (federada → [[PLAN-platform-review]] W3-T05).
> **Gate (b) de F3** — parte 2 de 2.
> **Owner real:** `prompt-engineer` + `data-engineer` (corrige `sre-devops` do plano dono — Layers 2/4 são LLM/prompt).

## Contexto

Implementação física de **W3-T05** ([[PLAN-platform-review]], hoje `blocked`).
Conteúdo de documento do usuário (extrato/IRPF) flui para prompts LLM em E5,
parecer e tool surface — superfície de prompt injection. Hoje não há camada de
sanitização: `pipeline/llm/prompts/_sanitization.py` **não existe**.

## Escopo

As 4 camadas de [[ADR-175]]:

1. **Sanitization** — `pipeline/llm/prompts/_sanitization.py` (strip de
   zero-width, neutralização de system-tags forjadas, markdown malicioso).
2. **System clause** — delimitação `<USER_DOC>...</USER_DOC>` no system prompt
   (PT-BR, comportamento consistente Claude/GPT).
3. **Pydantic strict** — já existe via [[ADR-026]]; confirmar cobertura.
4. **Adversarial fixtures** — `tests/test_prompt_injection_defense.py` com ≥1
   fixture por vetor (zero-width, system-tag, markdown injection).
5. **Telemetria** — `mathoms.llm.input_sanitized` (contagem de neutralizações).

## Critério de aceite

- `test_prompt_injection_defense.py` verde (≥1 fixture por vetor) — hard-block
  **mockado/determinístico** em PR (A21-KR5).
- No merge: flippar checkbox **W3-T05** em [[PLAN-platform-review]]
  `blocked → shipped` (regra anti-drift — não re-implementar em A22).

## Dependências

- Depende de l5 ([[ADR-175]] decidido).
- LLM-real nightly fica como **Should** (não bloqueia fechamento — depende de
  orçamento de provider).
