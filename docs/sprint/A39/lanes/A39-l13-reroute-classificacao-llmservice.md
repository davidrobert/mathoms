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
- **Resíduo declarado (corte da Fase 2):** ao shipar só a Fase 1, o path cru
  `anthropic.Anthropic()` **permanece** para PDF **imagem-only** até a Fase 2 —
  o bypass do choke-point **não fecha 100%** nesse incremento. Documentado para
  não virar débito perdido de novo.

## Critério de aceite (MLP — Fase 1; reescrito pelo pitch PM)

**Insight do PM:** desacoplar a alavanca de **risco** (budget hard-stop) das
alavancas **seguras** (telemetria, enum, anti-injection, `LLMCallLog`, cache-hook).
O re-route entrega as seguras "de graça e consistente" — aditivas. O budget é
*config* no `LLMService` → dá para rotear **sem armar** o hard-stop.

- `classify_by_llm` roteia pelo `LLMService.call`.
- Structured output com **enum** (`ClassificationLLMResult`, `dest_group`+`doc_type`
  como `Literal` — endurece o patch manual da [[A39.l11]] em contrato).
- Telemetria `mathoms.llm.*` com `prompt_name="classification"` (namespace paralelo
  proibido) + `LLMCallLog` populado em **100%** das chamadas de classificação.
- Anti-injection ([[ADR-175]]) na entrada de conteúdo do usuário.
- Prompt em home versionado (`config/prompts/classification.yaml`, `version:` semver).
- Cache **wired mas não load-bearing** (gated pelo determinismo do [[ADR-307]]).
- Budget hook **wired mas INERTE** (NULL/unlimited em dogfood+beta) — **armar** o
  hard-stop é rollout separado, soft-warn-first, com carve-out "classificação nunca
  hard-stopa, só avisa" (não se bloqueia a porta de entrada a ~110% do cap).
- Golden **LLM-free** N=3: 0 flips de `doc_type`/`dest_group` vs baseline;
  needs_review-rate no corpus congelado ±0; `rg` PII em fixtures = 0.

**Fora do MLP (fast-follow):** enforcement do budget; **Fase 2** (bloco `document`,
PDF-imagem); golden **real-LLM** owner-gated (k≥2, ~15-20 fixtures edge).

## Risco

Médio-alto — cross-cutting (boundary refactor + contrato do choke-point + budget em
chamada de maior volume). Mitigação: faseamento + MLP sem budget armado + co-design
senior-cto/data-engineer no PR de plumbing.

## Pitch / Priorização (PM · 2026-07-24)

> **Recomendação: Fase 1 → A40, lane P1 própria. Fase 2 → deferida (carona em
> refactor futuro da assinatura do choke-point). NÃO fechar na A39.**

**RICE** (não WSJF — cost-of-delay é baixo: a [[A39.l11]] já fechou o agudo):

| | Reach | Impact | Conf | Effort | RICE |
|---|---|---|---|---|---|
| Fase 1 (texto+JPG/PNG) | 8 | 2 | 0,8 | 0,5pm | **≈ 25,6** |
| Fase 2 (bloco `document`) | 3 | 1 | 0,5 | 1,0pm | **≈ 1,5** |

Gap 17× → ship Fase 1, adia Fase 2. **Não é P0** (l11 fechou determinismo +
misroute); Fase 1 = **P1 enabler**, Fase 2 = **P2**.

**Sprint-alvo A40, não A39:** a l13 **não move nenhum KR do A39** (KRs A–E são
parse/conservação E0→E2); o DoD do A39 (W0+W1) já está atingido (12/13). Cramar
pressiona a análise de rollout do budget que ela mesma exige. *A lane segue com id
`A39.l13` (origem no spin-off da l11) até o owner abrir a A40 — o move físico é a
abertura da sprint.*

**KR (armadilha de Goodhart):** *não* justificar com "reduzir custo LLM/mês" nem
"cache hit-rate" — essas métricas **não existem** para classificação hoje (a chamada
é cega). KR primário = **enablement/observabilidade** (0% → 100% observável) + enum-
contrato + guarda de 0-regressão. Custo/hit-rate viram mensuráveis **como resultado**,
com alvo em A40+ → **a l13 é pré-requisito** desses candidatos.

**Nuance BYOK:** o budget protege o *spend do usuário* (não COGS da plataforma);
NULL em dogfood. "Maior volume" = maior **frequência**, não maior **custo**
(classificação roda sobre preview; custo/mês é dominado pelo parecer).

**Handoffs:** `information-architect` (forma do `classification.yaml`); `senior-cto`
+ `data-engineer` (Fase 2 — assinatura compartilhada); `prompt-engineer` (golden
real-LLM + desenho de hit-rate do cache).
