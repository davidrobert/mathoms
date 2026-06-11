---
id: ADR-288
type: adr
title: "Catálogo de modelos LLM como fonte única + endpoint GET /llm/models (curado agora, dinâmico depois)"
status: Decidido
phase: "F1"
date: "2026-06-11"
relates_to:
  - "[[ADR-144]]"
  - "[[ADR-111]]"
  - "[[ADR-109]]"
  - "[[ADR-102]]"
supersedes: []
superseded_by: []
aliases: ["ADR 288", "llm models catalog", "lista de modelos llm"]
tags:
  - type/adr
  - status/decidido
  - area/backend
  - area/llm
---

# ADR-288 — Catálogo de modelos LLM como fonte única + endpoint `GET /llm/models`

**Status:** Decidido (F1 entregue; F2 dinâmico segue Roadmap nesta ADR) •
**Data:** 2026-06-11 • **Relaciona** [[ADR-144]]
(cache LLM Redis), [[ADR-111]] (stateless — proíbe cache in-memory),
[[ADR-109]]/[[ADR-102]] (response_model + snapshot OpenAPI).

## Contexto

A lista de modelos da aba LLM em `/config` é hardcoded no frontend
(`MODELS_BY_PROVIDER`, `LLMTab.tsx`) e está uma geração atrás (sem
`claude-opus-4-8`). Há **3 fontes desalinhadas** de "quais modelos
existem": a lista do frontend, `MODEL_PRICING`
(`pipeline/llm/pricing.py`) e o default `claude-sonnet-4-20250514`
repetido em **9+ call-sites de produção** (schemas, model DB,
`LLMConfig` do pipeline, parecer, fallbacks E0/E2, `PipelineTab.tsx`,
`config/pipeline.json`). Esse default é modelo **deprecated com
aposentadoria em 2026-06-15** — workspaces salvos com ele quebram em
runtime.

Bug correlato: a UI oferece providers `google` e `openrouter`, mas
`VALID_PROVIDERS` (backend) rejeita ambos — salvar falha 422. A UI
contorna o Google embutindo o prefixo `gemini/` no value do modelo.

## Decisão

1. **Catálogo curado como fonte única** em
   `pipeline/llm/models_catalog.py` (vive em `pipeline/` porque
   call-sites de pipeline não podem importar `backend`; o inverso é
   permitido). Exporta:
   - `MODELS_BY_PROVIDER` — lista curada por provider
     (`value`, `label`);
   - `default_model_for(provider)` — substitui o default datado nos
     call-sites de produção;
   - `DEPRECATED_MODELS` — set de modelos com aposentadoria anunciada.
   Invariante (teste): todo modelo curado tem
   `estimate_cost_usd(model, 1, 1) is not None` OU `pricing_known=False`
   explícito — chamando a função real (`_resolve_pricing` faz substring
   match; não reimplementar).
2. **Endpoint** `GET /workspaces/{id}/config/llm/models?provider=X` com
   `response_model=LLMModelsResponse` — itens
   `{value, label, source: "curated"|"provider", pricing_known}` +
   `fetched_dynamic: bool`. O recurso é global, servido sob namespace de
   workspace por conveniência de auth/tenancy (a key que enriquece na
   fase 2 é do tenant).
3. **Sinal de modelo deprecated sem migration** — campo
   `model_status: "ok" | "deprecated"` em `LLMConfigResponse`, derivado
   de `DEPRECATED_MODELS` (mesmo padrão de `api_key_status`). UI mostra
   banner pedindo atualização. Migration em massa foi rejeitada:
   sobrescreveria escolha explícita do usuário.
4. **Providers `google` e `openrouter` passam a ser válidos** —
   `VALID_PROVIDERS` (backend) + `SUPPORTED_PROVIDERS` (LiteLLM client;
   prefixos `gemini/` e `openrouter/`, env keys `GEMINI_API_KEY` e
   `OPENROUTER_API_KEY`). Remove o hack `gemini/` no value do frontend.
5. **Default `claude-sonnet-4-20250514` → `claude-sonnet-4-6`**
   (drop-in oficial, mesmo pricing $3/$15 MTok) via
   `default_model_for("anthropic")` nos call-sites.
6. **Frontend consome o endpoint** — `MODELS_BY_PROVIDER` do
   `LLMTab.tsx` é deletado; fetch on provider change; input de modelo
   customizado preservado.

### Fases

- **F1 (este PR):** itens 1–6 com endpoint servindo **apenas o catálogo
  curado** (`fetched_dynamic: false` sempre). Resolve o deprecated que
  aposenta em 4 dias e a desincronia das 3 fontes.
- **F2 (PR futuro, atrás de feature flag em `DEFAULTS` do
  `feature_flags_service`):** enriquecimento dinâmico — fetch
  `GET /v1/models` do provider com a key do workspace, merge com o
  curado (curado primeiro; novos com `source="provider"`), cache Redis
  **por workspace** (`mathoms:llm:models:v1:ws:{id}:{provider}`, TTL
  24h, via `LLMCacheBackend` de [[ADR-144]]), falha aberta (degrada pro
  curado). Ollama fica fora do dinâmico em prod (backend não alcança o
  host local do usuário). Antes de implementar F2, reavaliar
  `litellm.get_valid_models()` vs parsers próprios (build-vs-buy).

## Alternativas rejeitadas

- **Só atualizar a lista hardcoded** — trata sintoma; retorno garantido
  a cada release de modelo (~2 meses).
- **100% dinâmico sem curadoria** — lista do OpenAI vem poluída
  (embeddings/TTS), pricing fica órfão, fluxo sem key quebra.
- **Cache global alimentado pela key de um tenant** — bloqueado em
  revisão (senior-cto): ação do tenant A produziria artefato servido ao
  tenant B (acoplamento de erro/rate-limit, quota gasta por um em
  benefício de todos, trilha de auditoria confusa). Lista muda em escala
  de semanas; ganho de cache cross-tenant é marginal.
- **Data migration dos rows com modelo deprecated** — sobrescreve
  escolha explícita; o sinal `model_status` + banner cobre com risco
  zero.

## Consequências

- Modelo novo da Anthropic/OpenAI → 1 edit em `models_catalog.py`
  (+pricing se aplicável), zero deploy de frontend.
- `MODELS_BY_PROVIDER` (frontend) deixa de existir; OpenAPI snapshot
  ganha `LLMModelsResponse`.
- Workspaces com `claude-sonnet-4-20250514` salvos veem banner; nenhum
  dado é tocado.

## Critério de aceite (F1)

- Lista da UI vem 100% do endpoint; `MODELS_BY_PROVIDER` deletado do
  `LLMTab.tsx`.
- Teste de invariante catálogo↔pricing chamando `estimate_cost_usd`.
- `google`/`openrouter` passam o validator Pydantic; prefixos LiteLLM
  com teste.
- `model_status="deprecated"` para `claude-sonnet-4-20250514`.
- Call-sites de produção do default datado consumindo
  `default_model_for` (ou justificados no PR).
- `make update-openapi-snapshot` + suítes backend/pipeline/frontend
  verdes.
