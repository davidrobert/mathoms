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

As 4 camadas de [[ADR-175]], **com escopo confirmado pelo co-design de l5**
(`senior-cto` + `prompt-engineer`):

1. **Sanitization** — `pipeline/llm/prompts/_sanitization.py` (função pura,
   regex compilado): strip de zero-width/ANSI, padrões prompt-leak,
   **e auto-neutralização do próprio delimitador** (`<USER_DOC>`/`</USER_DOC>`
   no input do usuário). **Choke-point único:** aplicada dentro de
   `LLMService.call` (`pipeline/llm/litellm_client.py`) sobre `user_prompt`,
   **nunca** `system_prompt`. Chamada LLM fora do portão é proibida.
2. **System clause (sandwich)** — cláusula `<USER_DOC>...</USER_DOC>` antes do
   bloco + **reforço curto após** `</USER_DOC>` (PT-BR; mitiga recency bias).
   Eval cross-provider Claude/GPT-4 é gate de **produção** (nightly), não de
   merge.
3. **Pydantic strict** — já existe via [[ADR-026]]; **auditar** cobertura de
   `additionalProperties=false` em todos os output_schemas + inventariar
   campos string livres como superfície residual (não só "confirmar").
4. **Adversarial fixtures** — `tests/test_prompt_injection_defense.py` com ≥1
   fixture por vetor para **5 vetores**: `zero_width`, `system_tag`,
   `markdown_injection`, `delimiter_breakout`, `monetary_field_payload`.
   Para `monetary_field_payload` o assert é **destino `needs_review`** ([[ADR-027]]),
   não neutralização. Base64/idioma-misto: out-of-scope (follow-up nominal).
5. **Telemetria** — `mathoms.llm.input_sanitized{pattern}` emitida de dentro de
   `LLMService.call`; `pattern` é **enum fechado** (`zero_width`, `ansi_escape`,
   `system_tag`, `prompt_leak`, `delimiter_breakout`) — nunca o trecho casado
   (dados sensíveis).
6. **Reconciliar** `parecer_distiller._INJECTION_RE` ([[ADR-203]]): consome o
   sanitizer canônico da Layer 1 ou declara-se exceção justificada.

## Critério de aceite

- `test_prompt_injection_defense.py` verde (≥1 fixture por vetor, 5 vetores) —
  hard-block **mockado/determinístico** em PR (A21-KR5); assert de `needs_review`
  presente no vetor monetário.
- Teste prova que **todo** call-site de `LLMService.call` passa pela sanitização
  (teste no choke-point, não por stage).
- Grep de dados sensíveis em `tests/fixtures/pdf/adversarial/` com zero hits.
- No merge: flippar checkbox **W3-T05** em [[PLAN-platform-review]]
  `blocked → shipped` (regra anti-drift — não re-implementar em A22).

## Dependências

- Depende de l5 ([[ADR-175]] decidido).
- LLM-real nightly fica como **Should** (não bloqueia fechamento — depende de
  orçamento de provider).
