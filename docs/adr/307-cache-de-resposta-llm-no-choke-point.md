---
id: ADR-307
type: adr
title: "Cache de resposta LLM opt-in no choke-point (hook universal) + invariantes de drift"
status: Proposto
phase: W6-T02
date: "2026-07-06"
relates_to:
  - "[[ADR-111]]"
  - "[[ADR-173]]"
  - "[[ADR-175]]"
  - "[[ADR-210]]"
  - "[[ADR-233]]"
  - "[[ADR-260]]"
  - "[[ADR-261]]"
supersedes: []
superseded_by: []
aliases: ["ADR 307", "LLM response cache", "MLOps universal hooks"]
tags:
  - type/adr
  - status/proposto
  - area/llm
  - area/pipeline
  - area/finops
---

# ADR-307 — Cache de resposta LLM opt-in no choke-point + invariantes de drift

**Status:** Proposto • **Data:** 2026-07-06 • **Lane:** W6-T02 (PLATFORM_REVIEW).
Co-design: `data-engineer` + `prompt-engineer` (2026-07-06).

## Contexto

`LLMService.call` ([pipeline/llm/litellm_client.py](../../pipeline/llm/litellm_client.py))
é o choke-point único das chamadas LLM. Budget hard-stop e telemetria
(`LLMCallLog`) já são universais via `LLMCallHooks` injetado ([[ADR-173]],
W3-T01). **Cache de resposta, não:** só orchestrators do backend cacheiam
(parecer, section summaries — keys semânticas próprias); stages de pipeline
(E1.x, E2-*) **não podem** cachear porque `pipeline/**` não importa redis
(boundary). Cada re-run do dogfood re-paga a extração dos mesmos documentos.

**Bug latente descoberto:** `extract_comprovantes_bens` monta uma "cache key"
(content_hash + PROMPT_VERSION) e a passa como `stage=` — que vai direto para
`LLMCallLog.stage`, explodindo a cardinalidade da telemetria ([[ADR-260]]).
Nunca houve cache ali; a docstring promete "cache idempotente" que não existe.

## Decisão

1. **Protocol `LLMResponseCache`** (`get`/`set`) em `pipeline/llm/`, injetado
   no construtor do `LLMService` (paridade com `LLMCallHooks`); backend fornece
   Redis, testes injetam fake em memória. Default `None` = sem cache.
2. **Opt-in por call-site:** `use_cache: bool = False` em `call()`. V1 liga em
   E2 `extract_comprovantes_bens` (corrigindo o bug do `stage=`); demais
   extrações (E1.x, E2-informes) podem aderir depois sem mudança de mecanismo.
3. **Key construída no choke-point** (função única testável):
   `mathoms:llm:resp:{stage}:{prompt_version}:{sha256(model + system_prompt +
   user_prompt_pós_sanitize + schema_name + temperature + max_tokens + seed +
   image_sha256)[:32]}`. Content-hash ⇒ invalidação automática quando o prompt
   muda (superset da invalidação por versão); `stage`/`prompt_version` ficam
   **fora do material hasheado** (prefixo legível para scan/flush). Trade-off
   aceito: bump de versão sem mudança de conteúdo (raro; o gate de
   [[ADR-233]] força bump apenas quando conteúdo muda) invalida via prefixo —
   custo de 1 re-extração.
4. **Guardrail duro de determinismo:** `use_cache=True` com
   `temperature > 0.0` ⇒ `ValueError` (fail-fast em boundary). Cache congela
   uma amostra; a temp>0 isso corrompe variância silenciosamente (ex.: as ≥20
   gerações do parecer que gateiam A26). Call-site que quer cache roda temp=0
   explícito.
5. **Semântica de hit/miss:** hit pula provider e `check_budget`, **não grava
   `LLMCallLog`** (tabela é verdade de custo real) e emite contadores
   estruturados `mathoms.llm.cache_hit|cache_miss` (logger nomeado, labels
   `stage`/`prompt_version` — nunca o payload). Write só em retorno validado
   de `call()` (nunca exceção, nunca erro); valor = `model_dump_json()` cru do
   schema (schemas não carregam PII bruta; CPF mascarado é enriquecimento
   Python pós-LLM — invariante deste mecanismo). TTL 7 dias.
6. **Parecer (E6) e section summaries (E5) NÃO migram:** suas keys semânticas
   (`RED_LINES_VERSION`/`EVIDENCIA_VERIFICATION_VERSION`, `snapshot_hash`)
   invalidam por eixos que não estão no content-hash do prompt. Camadas
   distintas: este cache é resposta efêmera em runtime; [[ADR-261]] governa
   artifacts persistidos e re-extração em massa — ortogonais.
7. **Drift em 3 camadas com donos distintos** (nomeação precisa, [[ADR-210]]):
   - **Invariantes de key** (`tests/test_llm_drift.py`, todo PR, LLM-free):
     todo schema LLM declara `PROMPT_VERSION` semver; key muda quando
     conteúdo/temperature/max_tokens muda e é estável caso contrário;
     `sanitize_and_wrap` é determinístico (2 chamadas ⇒ mesma key — dependência
     de [[ADR-175]]: sandwich nunca pode injetar nonce).
   - **Golden de extração LLM-free** (todo PR): fixture sintética PII-zero com
     expected output servido via cache fake pré-populado — testa a cadeia de
     materialização (payload, máscara de CPF, needs_review) sem token.
   - **Drift real**: parecer coberto por `planner-golden-monthly` +
     `llm-cross-provider-smoke` + lineage-eval nightly; extração ganha job
     nightly próprio (3-5 casos sintéticos, 1 trial, assertions estruturais,
     auto-issue) — follow-up F2 desta ADR, PR separado.

## Gate bloqueante pré-implementação

Cache só entra se **2 execuções sobre o mesmo documento produzem
`user_prompt` byte-idêntico** (teste de regressão). Texto extraído
não-determinístico ⇒ miss perpétuo ⇒ cache inútil para o caso motivador
(re-run do dogfood) — corrigir o não-determinismo vem antes.

## Consequências

- Re-run do dogfood deixa de re-pagar extração idêntica (FinOps direto no
  loop de iteração do REPORT_TRUST).
- `LLMCallLog.stage` volta a ser descritivo ([[ADR-093]]) em comprovantes.
- Global novo (client Redis do cache) registrado em
  `docs/reference/STATELESS_AUDIT.md` §2 — singleton lazy idempotente,
  [[ADR-111]] (b).
- LGPD: payload financeiro fica ≤7d em namespace dedicado
  (`mathoms:llm:resp:*`, flush cirúrgico), valor nunca logado, sem CPF
  (teste de regressão com regex).

## Critério de aceite

- `check_pipeline_boundaries` verde; fake em `tests/fakes/`.
- Hit: 0 chamadas ao provider, budget não consultado, `LLMCallLog` não cresce,
  contador emitido. Miss em qualquer campo hasheado alterado.
- `ValueError` em `use_cache and temperature > 0` (teste).
- Gate de determinismo do `user_prompt` passa para o call-site opt-in.
- Payload cacheado sem CPF (regex) e nunca logado.
- Flip `Decidido` no merge do PR de implementação.
