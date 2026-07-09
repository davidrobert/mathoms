---
id: A21.l6
type: lane
title: "W3-T05 — defesa de injeção LLM (4 camadas + adversarial fixtures + telemetria)"
sprint: A21
plan: PLAN-launch-trust
status: shipped
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
  - status/shipped
  - priority/p0
  - area/llm
  - area/seguranca
---

# A21.l6 — W3-T05 defesa de injeção LLM (implementação)

> **Plano:** [[PLAN-launch-trust]] §F3-O3 (federada → [PLAN-platform-review](../../../archive/PLATFORM_REVIEW_PLAN-2026-07-08.md) W3-T05).
> **Gate (b) de F3** — parte 2 de 2.
> **Owner real:** `prompt-engineer` + `data-engineer` (corrige `sre-devops` do plano dono — Layers 2/4 são LLM/prompt).

## Contexto

Implementação física de **W3-T05** ([PLAN-platform-review](../../../archive/PLATFORM_REVIEW_PLAN-2026-07-08.md), hoje `blocked`).
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
- No merge: flippar checkbox **W3-T05** em [PLAN-platform-review](../../../archive/PLATFORM_REVIEW_PLAN-2026-07-08.md)
  `blocked → shipped` (regra anti-drift — não re-implementar em A22).

## Achado de implementação (2026-05-30)

Entregue em `agent/a21-l6-prompt-injection-defense`. As 6 partes:

- **Layer 1** — `pipeline/llm/prompts/_sanitization.py` (função pura, regex
  compilado = constante ADR-111): `sanitize_user_content` + `wrap_user_doc` +
  `sanitize_and_wrap` + `contains_injection_pattern` (fonte canônica de
  detecção). Strip de zero-width/bidi, ANSI, system-tag, prompt-leak, e
  auto-neutralização do delimitador.
- **Layer 2** — sandwich PT-BR em `wrap_user_doc` (cláusula antes +
  `<USER_DOC>`…`</USER_DOC>` + reforço depois).
- **Choke-point** — `sanitize_and_wrap(user_prompt)` aplicado em
  `LLMService.call` sobre `user_prompt` (string E bloco multimodal `text`);
  `system_prompt` intocado. Teste no portão prova herança por todo call-site.
- **Telemetria** — logger nomeado `mathoms.llm.input_sanitized` emite só o
  `pattern` (enum fechado), nunca o trecho casado.
- **Layer 4** — `tests/test_prompt_injection_defense.py` (14 testes): 5 vetores
  + choke-point + system-prompt-intacto + monetário→`LLMValidationError`.
  Fixtures são strings in-test (zero-PII, determinístico) — **não** há
  `tests/fixtures/pdf/adversarial/` (vetores não precisam de PDF binário no
  gate determinístico; LLM-real nightly é follow-up).
- **Reconciliação ADR-203** — `parecer_distiller` consome
  `contains_injection_pattern` (regex local `_INJECTION_RE` removido).

**Layer 3 — finding do audit (não-flip, follow-up).** `extra="forbid"` cobre
apenas **2/10** output_schemas (`CRLVPayload`, `InformeAluguelExtract`). 3 usam
`extra="allow"` (`ApolicePayload`, `IRPFFullOutput`, `InformeRendimentosBase`) —
**superfície residual**: campo forjado propaga ao model (domínio só lê campos
conhecidos, mas `model_dump()` carregaria o extra). 5 usam default `ignore`
(extra silenciosamente dropado — seguro p/ injeção, mas não sinaliza). Flippar
`allow→forbid` é mudança de comportamento de extração (LLM legítimo pode
retornar campo extra tolerado) — exige paridade de extração + sign-off
`prompt-engineer`/`data-engineer`, fora do escopo de A21 (pure-engineering,
sem risco de regressão de domínio). **Follow-up:** lane dedicada para flippar
os 3 `allow`→`forbid` com goldens de extração, ou justificar cada `allow`.

## Dependências

- Depende de l5 ([[ADR-175]] decidido).
- LLM-real nightly fica como **Should** (não bloqueia fechamento — depende de
  orçamento de provider).
