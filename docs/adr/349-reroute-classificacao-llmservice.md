---
id: ADR-349
type: adr
title: "Rotear classify_by_llm pelo choke-point LLMService (instrumentação: budget, cache, telemetria, enum)"
status: Proposto
phase: A39
date: "2026-07-24"
relates_to:
  - "[[ADR-081]]"
  - "[[ADR-110]]"
  - "[[ADR-173]]"
  - "[[ADR-307]]"
  - "[[ADR-175]]"
  - "[[ADR-348]]"
tags:
  - type/adr
  - status/proposto
  - area/pipeline
  - area/dados
---

# ADR-349 — Rotear classificação de documentos pelo LLMService

**Status:** Proposto (A39) · **Data:** 2026-07-24 · **Lane:** re-route classificação (P1, a criar)

## Contexto

`scripts/route_documents.py::classify_by_llm` usa `anthropic.Anthropic()` **cru**,
que **bypassa o choke-point instrumentado** `pipeline/llm/litellm_client.py::LLMService.call`.
É a chamada LLM de **maior volume** do produto (todo upload ambíguo, via
[[ADR-081]]) e hoje roda **sem**:

- **budget cap** ([[ADR-173]]) — pode consumir custo sem hard-stop;
- **cache** ([[ADR-307]]) — candidato #1 (hash de conteúdo → classificação estável);
- **validação de enum na saída** — `json.loads` + `.get()` cru; `dest_group`
  alucinado misrota o documento ([[ADR-348]] mitigou com validação manual, mas o
  choke-point valida via Instructor no schema);
- **telemetria estruturada** `mathoms.llm.*` ([[ADR-110]]) + `LLMCallLog`/drift;
- **anti-injection** ([[ADR-175]]).

[[ADR-348]] fechou os dois riscos **agudos** (determinismo + misroute) com adições
puras, mas conscientemente deixou a lacuna de instrumentação — cabear os primitivos
à mão no path cru seria **build-then-delete** (exigem emitter, DB session, budget
hook; `LLMCallLog` nem funciona no path CLI-isolado).

## Decisão (proposta)

Rotear `classify_by_llm` pelo `LLMService.call`. Ganha de graça e consistente:
`temperature`/`seed` (best-effort), structured output com **enum** (Instructor +
auto-retry), `mathoms.llm.*` com label `prompt_name="classification"`,
`LLMCallLog`/drift, budget, cache, anti-injection.

Escopo líquido pós-reroute: (1) schema Pydantic `ClassificationLLMResult`
(`dest_group`/`doc_type` como `Literal`, derivado de `_DEST_GROUPS` de [[ADR-348]]);
(2) mover o prompt inline para home versionado (`config/prompts/classification.yaml`
com `version:` semver — forma é escopo do `information-architect`); (3) sinal de
drift próprio (share `source=llm_fallback`, needs_review-rate por `dest_group`);
(4) golden owner-gated (real-LLM, `dest_group`+`doc_type` exact-match em ~15-20
fixtures edge PII-zero, k≥2 repetições estáveis) + workflow dedicado.

## Risco técnico primário — path PDF-imagem

`LLMService.call` expõe `image_bytes` (bloco `image`); o path atual manda bloco
`type: document` (base64 do PDF). **Faseamento:**

- **Fase 1** — re-roteia texto + JPG/PNG (mapeiam limpo via `image_bytes`).
- **Fase 2** — estende o choke-point para o bloco `document` (toca a assinatura
  usada por todos os stages LLM — co-design `senior-cto` + `data-engineer`).

## Consequências / risco de rollout

- Pôr a chamada de maior volume sob budget ([[ADR-173]]) pode **hard-stop uploads**
  a ~110% do cap → exige análise de risco + rollout próprios (não é ligar e sair).
- `scripts/` CLI-isolado precisa de `LLMService` injetável (backend tem
  `WorkspaceContext`; CLI monta `LLMConfig` bare com budget/cache/metrics no-op).
- Fecha a lacuna de observabilidade da [[ADR-348]].

## Por que ADR `Proposto` (não implementado aqui)

Cross-cutting em 3 eixos (boundary refactor + contrato do choke-point +
comportamento sob budget) → P1-shaped, cai na política "ADR `Proposto` antes de PR
P0/P1". Enfiar no rabo de um P2 trailing (l11) seria dead-code-shipping. Lane
própria P1, a priorizar (`product-manager`) antes de fechar a A39.
