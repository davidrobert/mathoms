---
id: ADR-144
type: adr
title: "`section_summaries` LLM-driven em E5 com cache + fallback determinístico (v2.9)"
status: Decidido
phase: "Fase 1 — fundação arquitetural; implementação em Fase 2 sob lane v2.9"
date: "2026-04-27"
relates_to: ["[[ADR-024]]", "[[ADR-025]]", "[[ADR-090]]", "[[ADR-097]]", "[[ADR-105]]", "[[ADR-110]]", "[[ADR-111]]", "[[ADR-122]]", "[[ADR-127]]", "[[ADR-128]]", "[[ADR-132]]"]
supersedes: ["[[ADR-122]]", "[[ADR-111]]", "[[ADR-127]]", "[[ADR-144]]"]
superseded_by: []
aliases: ["ADR 144"]
tags:
  - type/adr
  - status/decidido
size_lines: 109
---

# ADR-144 — `section_summaries` LLM-driven em E5 com cache + fallback determinístico (v2.9)

**Status:** Decidido (Fase 1 — fundação arquitetural; implementação em Fase 2 sob lane v2.9) • **Data:** 2026-04-27

**Supersedes (parcial):** parte LLM de [ADR-122](#adr-122--chart_conclusions-e-section_summaries-em-modo-híbrido-template--llm) — o desenho híbrido continua válido (chart_conclusions determinístico, section_summaries LLM), mas ADR-122 foi escrita antes de ADR-111 (stateless rigoroso) consolidar e antes de ADR-127/128 fixarem o contrato `ArtifactStore` para LLM stages. ADR-144 fecha as lacunas operacionais de cache, fallback, telemetry e diferenciação cache-runtime vs ArtifactStore.

**Contexto:**
- Hoje E5 produz `section_summaries` via templates determinísticos puros — derivers em `pipeline/domain/services/derivers/section_summaries.py` (backend) e `deriveSectionSummary` em `frontend/src/lib/conclusionUtils.ts` (frontend, fallback do snapshot). Resultado funciona, mas é narrativamente engessado: 10 textos por relatório, todos no mesmo registro mecânico, sem contextualizar tendência ou ressaltar o que mudou desde o snapshot anterior.
- ADR-122 já decidiu o desenho geral (híbrido template+LLM). Faltava uma ADR operacional que fechasse: (i) qual stack LLM usar, (ii) onde mora o cache, (iii) qual é o fallback se LLM falha, (iv) como a telemetria diferencia regime LLM vs determinístico, (v) como esta dependência convive com ADR-111 (stateless) e ADR-127/128 (ArtifactStore para LLM stages).
- E5 hoje é **100 % determinístico**. Todas as outras stages que tocam LLM (E1, E1.5, E2-llm, E7-review-llm) já estão estabilizadas em LiteLLM + Instructor com Pydantic ([ADR-105](#adr-105--llm-stages-escrevem-via-artifactstore-e1-e-e7-review-llm-não-migram-a6a) / [ADR-127](#adr-127--e1-members-persiste-via-artifactstore) / [ADR-128](#adr-128--e7-review-llm-lêescreve-via-artifactstore)). Esta ADR é a primeira intrusão de LLM em E5 e estabelece o padrão para futuras (e.g., v3 pode upgrade `ChangelogEntry.summary` para LLM reusando os mesmos primitives).

**Alternativas consideradas e descartadas:**
1. **Templates "ricos" sem LLM** (mais condicionais, mais variantes): cresce combinatorialmente, vira spaghetti, e não resolve o problema de tom narrativo. Rejeitado.
2. **Input manual do consultor**: não escala — produto é self-serve. Rejeitado já em ADR-122.
3. **OpenAI direto via SDK**: rompe paridade com E1/E1.5/E2-llm que usam LiteLLM. Rejeitado.
4. **Cache em SQLite local / disco**: viola ADR-111 (multi-worker). Rejeitado.
5. **Cache via `ArtifactStore`**: confunde camadas — `ArtifactStore` é para artefatos de pipeline (input/output de stage, parte do lineage do `ReportRun`); cache LLM é otimização de runtime, não artefato semanticamente versionado. Diferenciação preservada.

**Decisão:**

### 1. Stack LLM — paridade com E1/E1.5/E2-llm/E7-review-llm
- **LiteLLM + Instructor + Pydantic** (mesma stack das outras LLM stages — [ADR-024 LiteLLM, ADR-025 BYOK, ADR-105]).
- **Saída tipada** (`SectionSummaryResult` Pydantic) — nunca string livre. Campos: `summary_md: str`, `tone: Literal["neutral","positive","warning"]`, `key_metric_ref: Optional[str]`. **Money não aparece**: section_summaries são prosa narrativa; se o LLM emitir número monetário inline, o validator Pydantic exige `Decimal`-string e o renderer formata via `Money` ([ADR-090](#adr-090--decimal-para-valores-monetários)). Em prática o prompt instrui referenciar métrica por id (`key_metric_ref`) e o frontend resolve para `<MonetaryValue/>` — assim o LLM nunca formata BRL.
- **Determinismo máximo viável**: `temperature=0`, `seed` fixo por `(section_id, snapshot_hash)`. Não é determinismo absoluto (provedor não garante), mas reduz drift run-a-run a < 1 %.
- **Modelo default**: **Claude Haiku 4.5** (custo) — Sonnet 4.6 disponível como opt-in via `pipeline.json:llm.section_summaries.model_override` para clientes premium ou A/B test editorial.

### 2. Cache — Redis (preferido) com fallback Postgres+TTL
- **Cache key:** `mathoms:llm:section_summary:{workspace_id}:{snapshot_hash}:{section_id}`. `snapshot_hash` é o hash determinístico do payload de seção que entra no prompt (NÃO o hash do snapshot inteiro — duas seções do mesmo relatório têm hashes diferentes).
- **TTL: 24h** (revisado para baixo vs ADR-122 que falava 7d). Justificativa: relatórios são gerados sob demanda, não automaticamente; usuário que reabre relatório no mesmo dia merece resposta cached, mas relatório re-gerado no dia seguinte (mesmo snapshot, mesma seção) deve revalidar — modelo pode ter sido atualizado, prompt pode ter evoluído. 24h é o ponto de Pareto.
- **Storage:** Redis (preferido — já usado em ADR-111 cache layer, ADR-117 invitation rate limit). Adapter pequeno em `backend/app/services/llm_cache.py` com interface mínima (`get(key) -> Optional[str]`, `set(key, value, ttl_s)`).
- **Fallback de storage**: se Redis indisponível em deploy minimalista (Mathoms self-host, single-node), tabela Postgres `llm_response_cache(key TEXT PRIMARY KEY, value JSONB, expires_at TIMESTAMPTZ)` com varredura batch via Celery beat (`expire_llm_cache` cron 1×/h). Mesmo contrato de adapter; escolha por env var `LLM_CACHE_BACKEND={redis|postgres}` (default `redis`).
- **PROIBIDO** (ADR-111): `lru_cache`, `cached_property`, dict/`set` global em módulo, file lock. Esta ADR explicitamente fecha a porta — auditável por `dev/check_pipeline_boundaries.py` + `backend/tests/integration/test_multi_worker_concurrency.py`.

### 3. Fallback determinístico — LLM nunca é caminho crítico
- Qualquer falha do LLM (timeout, rate limit Anthropic 429, erro 5xx do provedor, JSON inválido após retry, cache backend down) **degrada silenciosamente** para os derivers determinísticos atuais (`pipeline/domain/services/derivers/section_summaries.py` no backend, `deriveSectionSummary` no frontend).
- **Retries**: 1 retry com backoff 500ms para erro transiente; 2ª falha → fallback. Sem retry indefinido.
- **Visibilidade do fallback**: nenhuma marca visual no relatório ("este texto é fallback") — usuário não diferencia. Fallback é registrado em telemetria (`fallback_used=true`) e em `qa_log.md` por workspace para diagnóstico interno.
- **Princípio**: relatório nunca falha por causa de LLM. LLM é enhancement; produto sem LLM continua entregando valor.

### 4. Telemetria — `fin.classification_telemetry`-style logger
- Logger novo `mathoms.llm.section_summaries` (namespace consistente com `mathoms.classification` de `classify_document`).
- **Campos por chamada** (sem PII; section_id é id de layout, não conteúdo do relatório):
  - `section_id` (string canônica do `report_layout.yaml`)
  - `snapshot_hash` (truncado a 12 chars)
  - `latency_ms` (int)
  - `cache_hit` (bool)
  - `fallback_used` (bool — true se degradou para deriver determinístico)
  - `model` (string — `"claude-haiku-4.5"` ou override)
  - `prompt_tokens`, `completion_tokens` (int)
  - `cost_usd` (Decimal-string, 6 casas — calculado pelo adapter usando pricing por modelo em `config/llm_pricing.json`)
  - `error_class` (string opcional — `"timeout" | "rate_limit" | "invalid_json" | "provider_5xx"` ou `null`)
- **Sem** logging do prompt ou resposta (são dados financeiros agregados — passam pelo princípio "PII fora do LLM" mas mantemos o log estritamente técnico para evitar vazamento via observabilidade).
- Log JSON via `mathoms.*` ([ADR-110](#adr-110--structured-json-logging--opentelemetry-bootstrap-a6f3)). Agregação em `qa_log.md` por workspace é opcional e roda offline (sidecar batch).

### 5. Custo — estimativa documentada
Prompt típico de section_summary tem ~2 k tokens de input (snapshot data filtrada para a seção + instruções de tom + few-shot examples) e ~500 tokens de output. Por relatório: 10 seções × (2 000 in + 500 out).

| Modelo | Pricing (USD / MTok, 2026-04 vigente) | Input cost | Output cost | **Total / relatório** |
|---|---|---|---|---|
| **Claude Haiku 4.5 (default)** | $1.00 in / $5.00 out | 10 × 2 000 / 1 e6 × $1.00 = $0.020 | 10 × 500 / 1 e6 × $5.00 = $0.025 | **~$0.045** |
| Claude Sonnet 4.6 (premium opt-in) | $3.00 in / $15.00 out | $0.060 | $0.075 | **~$0.135** |

Com cache hit ratio esperado de ~60 % (usuário reabre relatório no mesmo dia, TTL 24h), custo amortizado por **relatório novo** cai para ~$0.018 (Haiku) ou ~$0.054 (Sonnet). **Cap mensal por workspace** monitorado em telemetria — alarme se ultrapassar $5/mês (sinaliza loop bug ou abuso).

### 6. Coordenação com ADRs vigentes — diferenciações explícitas

| ADR | Como ADR-144 se relaciona |
|---|---|
| [ADR-105](#adr-105--llm-stages-escrevem-via-artifactstore-e1-e-e7-review-llm-não-migram-a6a) | Padrão de LLM em pipeline já estabelecido. v2.9 segue, **mas** seu output (`section_summaries`) é parte do snapshot E5 (já persistido por E5 em `analise_financeira-5_analysis.json`), não artefato novo separado — não cria nova `_STAGE_TO_DIR` entry. |
| [ADR-111](#adr-111--stateless-rigoroso-padrão-e-gate-empírico-a6f6) | Cache **deve** ser Redis ou Postgres com TTL. `lru_cache`/`cached_property`/global dict **proibidos**. Esta ADR é o ponto de aplicação do princípio em E5. |
| [ADR-122](#adr-122--chart_conclusions-e-section_summaries-em-modo-híbrido-template--llm) | ADR-144 implementa o **branch LLM** do híbrido para `section_summaries`. `chart_conclusions` permanece determinístico — ADR-122 não é descartada, é refinada nos pontos operacionais. |
| [ADR-127](#adr-127--e1-members-persiste-via-artifactstore) / [ADR-128](#adr-128--e7-review-llm-lêescreve-via-artifactstore) | **NÃO confundir cache LLM com ArtifactStore**: ArtifactStore é para artefatos do pipeline (input/output de stage, parte do lineage do `ReportRun`, sujeito a `pipeline_artifacts` lifecycle [ADR-132]). Cache LLM é otimização de runtime — efêmero, TTL 24h, sem lineage, fora do `ReportRun` graph. Diferenciação codificada: `LLMCacheBackend` em `backend/app/services/llm_cache.py`, distinto de `ArtifactStore`. |
| [ADR-148](#adr-148--snapshotchangelogbuilder-comparações-mês-a-mês-de-relatório) (v2.D.1) | v2.9 é **independente** de v2.D.1. v2.D.1 entrega `ChangelogEntry.summary` determinístico (template). v3 (lane futura, fora desta ADR) pode upgrade `summary` para LLM reusando os primitives definidos aqui (`LLMCacheBackend`, telemetry logger, fallback pattern). v2.9 e v2.D.1 podem mergear em qualquer ordem. |
| [ADR-090](#adr-090--decimal-para-valores-monetários) | Section summaries são prosa; LLM não emite valor monetário inline. Se o prompt evoluir e isso virar necessário, validator Pydantic exige `Decimal`-string + renderer formata via `Money`. |
| [ADR-110](#adr-110--structured-json-logging--opentelemetry-bootstrap-a6f3) | Telemetria via namespace `mathoms.llm.section_summaries`, JSON, sem PII. |
| [ADR-024 / ADR-025] | LiteLLM + BYOK — paridade com demais stages. |

### 7. Anti-escopo desta ADR
- **NÃO** define a Pydantic schema concreta de `SectionSummaryResult` (Fase 2).
- **NÃO** define o conteúdo do prompt em `config/prompts/section_summaries.yaml` (Fase 2 — sujeito a evolução editorial sem nova ADR salvo se mudar contrato de saída).
- **NÃO** define o adapter Redis concreto nem migration Postgres (Fase 2).
- **NÃO** marca v2.9 como ✅ no BACKLOG (continua 🚧 até Fase 2 mergear).

**Consequências:**
- ✅ Qualidade editorial real em 10 textos narrativos por relatório — diferencial vs. v1.
- ✅ Padrão de LLM-em-runtime estabelecido para reuso futuro (v3 changelog, eventuais executive summary, etc.) sem precisar nova ADR estrutural.
- ✅ Cache + fallback garantem que LLM é enhancement, não single-point-of-failure.
- ⚠️ Custo recorrente: ~$0.018–$0.054 por relatório novo (com cache 60 %). Para 1 000 relatórios/mês = $18–$54/mês — aceitável para fintech B2C; monitorar com cap por workspace.
- ⚠️ Latência: ~2–5 s por seção sequencial. Mitigação: paralelizar 10 seções via `asyncio.gather` + Instructor async; prazo total ~3–6 s. Ainda assim, geração de relatório passa de "instantânea" (~200 ms) para "alguns segundos" — UX precisa indicador de progresso.
- ⚠️ Rate limit Anthropic: 50 req/min default. 10 seções/relatório = 5 relatórios concorrentes batem o teto. Fallback determinístico cobre o overflow; em escala maior, solicitar tier upgrade ou batchear via Anthropic Batch API (lane futura, fora desta ADR).
- ⚠️ Cache invalidation por mudança de `snapshot_hash`: aceito — relatório é geração eventual, não hot path; revalidar quando snapshot muda é semanticamente correto.
- ❌ Não-determinismo residual entre cache misses (mesmo input pode produzir variação narrativa em runs diferentes). Mitigado por `temperature=0` + seed + cache 24h. Aceito como custo do regime LLM; alternativa (templates) já considerada e descartada acima.
- ❌ Primeiro consumidor real de Redis em pipeline (até hoje Redis era só backend session cache + Celery broker). Adiciona dependência operacional ao deploy mínimo. Mitigado pelo fallback Postgres+TTL.

**Plano de adoção (Fase 2 — fora desta ADR):**
1. Service `pipeline/domain/services/section_summary_generator.py` com Pydantic config tipado ([ADR-097](#adr-097--extract-then-refactor-estratégia-de-decomposição-de-e3_reconcilepy) D2/D3) — não recebe `StageConfig` inteiro nem `Path`; conversão é do adapter.
2. `LLMCacheBackend` protocol + `RedisLLMCache` / `PostgresLLMCache` em `backend/app/services/llm_cache.py`.
3. Prompt template em `config/prompts/section_summaries.yaml` (paridade com `chart_conclusions.yaml`).
4. Fallback path em E5 — invoca `derivers/section_summaries.py` se generator retorna `None` ou levanta.
5. Frontend `conclusionUtils.ts` lê `section_summaries[i]` do snapshot se presente, senão deriva.
6. Goldens em `tests/test_e5_section_summaries.py` com fakes (não bate API real em CI; usa `RecordedLLMResponseFake` por hash).
7. Telemetria + alarme de cap mensal.
8. Toggle `pipeline.json:llm.section_summaries.enabled` (default `true`) — permite desligar globalmente em incidente sem deploy.

**Gate de Fase 2**: goldens verdes + custo telemetrado + ADR-144 mergeada em `main`.

**Relaciona-se a:** [ADR-024 LiteLLM], [ADR-025 BYOK], [ADR-090](#adr-090--decimal-para-valores-monetários), [ADR-097](#adr-097--extract-then-refactor-estratégia-de-decomposição-de-e3_reconcilepy), [ADR-105](#adr-105--llm-stages-escrevem-via-artifactstore-e1-e-e7-review-llm-não-migram-a6a), [ADR-110](#adr-110--structured-json-logging--opentelemetry-bootstrap-a6f3), [ADR-111](#adr-111--stateless-rigoroso-padrão-e-gate-empírico-a6f6), [ADR-122](#adr-122--chart_conclusions-e-section_summaries-em-modo-híbrido-template--llm), [ADR-127](#adr-127--e1-members-persiste-via-artifactstore), [ADR-128](#adr-128--e7-review-llm-lêescreve-via-artifactstore), [ADR-132](#adr-132--lifecycle-scoping-de-pipeline_artifacts-workspace-vs-run). Lane operacional: [`docs/agent_prompts/track_report_v2.md` §3 v2.9](agent_prompts/track_report_v2.md).
