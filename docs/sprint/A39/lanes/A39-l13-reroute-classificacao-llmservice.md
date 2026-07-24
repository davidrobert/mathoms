---
id: A39.l13
type: lane
title: "Re-route: classify_by_llm pelo choke-point LLMService (budget + cache + telemetria + enum via Instructor)"
sprint: A39
status: planned
priority: P1
branch_slug: a39-l13-reroute-classificacao-llmservice
adrs: ["[[ADR-349]]"]
depends_on: ["[[A39.l11]]"]
tags:
  - type/lane
  - sprint/a39
  - status/planned
  - priority/p1
  - area/pipeline
  - area/dados
---

# A39.l13 — `reroute-classificacao-llmservice` (fast-follow da [[A39.l11]])

## Origem

Spin-off do co-design da [[A39.l11]] (senior-cto + prompt-engineer). A l11 fechou
os riscos **agudos** da classificação LLM (determinismo + misroute) de forma
cirúrgica; esta lane fecha a **doença de fundo**: `classify_by_llm` usa
`anthropic.Anthropic()` cru, bypassando o choke-point instrumentado
`LLMService.call`. Canônica: [[ADR-349]] (`Proposto`).

## Problema

A chamada LLM de **maior volume** do produto (todo upload ambíguo, [[ADR-081]])
roda **sem** budget ([[ADR-173]]), cache ([[ADR-307]]), validação de enum na saída
(via Instructor), telemetria `mathoms.llm.*` ([[ADR-110]]) nem anti-injection
([[ADR-175]]) — tudo que o choke-point já entrega de graça e consistente.

## Escopo (ver [[ADR-349]])

- Rotear `classify_by_llm` pelo `LLMService.call` (`scripts/` CLI-isolado precisa
  de `LLMService` injetável; backend tem `WorkspaceContext`).
- Schema `ClassificationLLMResult` (`dest_group`/`doc_type` `Literal`, derivado de
  `_DEST_GROUPS`); prompt para home versionado (`config/prompts/classification.yaml`,
  `version:` semver — forma: `information-architect`).
- Golden owner-gated real-LLM: `dest_group`+`doc_type` exact-match, ~15-20 fixtures
  edge PII-zero, k≥2 repetições estáveis + workflow dedicado.
- Drift: share `source=llm_fallback` + needs_review-rate por `dest_group`.
- **Faseamento (risco PDF-imagem):** Fase 1 texto + JPG/PNG (mapeiam limpo via
  `image_bytes`); Fase 2 estende o choke-point p/ o bloco `document` (base64 PDF).

## Critério de aceite

- `classify_by_llm` roteia pelo `LLMService.call`; enum validado no schema.
- Golden owner-gated verde (workflow dedicado, não por-PR).
- Telemetria `mathoms.llm.*` com `prompt_name="classification"` (namespace paralelo
  proibido); budget + cache ativos com análise de rollout (hard-stop a ~110%).

## Risco

Médio-alto — cross-cutting (boundary refactor + contrato do choke-point + budget em
chamada de maior volume). Mitigação: faseamento + co-design senior-cto/data-engineer
no PR de plumbing. **Priorização e sprint-alvo a definir (`product-manager`)** — P1,
mas pode escorregar para A40; registrado aqui para não virar débito perdido.
