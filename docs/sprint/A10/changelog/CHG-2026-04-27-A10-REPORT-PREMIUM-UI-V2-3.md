---
id: CHG-2026-04-27-A10-REPORT-PREMIUM-UI-V2-3
type: changelog-entry
date: "2026-04-27"
sprint: A10
adrs: ["[[ADR-090]]", "[[ADR-097]]", "[[ADR-110]]", "[[ADR-111]]", "[[ADR-127]]", "[[ADR-144]]"]
commits: ["22627e6", "5a1142d", "c0a79df", "d2b1827", "93992c5"]
summary: |
  Report Premium UI v2.9 — LLM section_summaries em E5 ✅ (2026-04-27). - **Report Premium UI v2.9 — LLM section_summaries em E5 ✅ (2026-04-27):** Fase 2 da [ADR-144](DECISIONS.md#adr-144--section_summaries-llm-driven-em-e5-com-cach
tags:
  - type/changelog-entry
  - sprint/a10
---


# Report Premium UI v2.9 — LLM section_summaries em E5 ✅ (2026-04-27)

- **Report Premium UI v2.9 — LLM section_summaries em E5 ✅ (2026-04-27):**
  Fase 2 da [ADR-144](DECISIONS.md#adr-144--section_summaries-llm-driven-em-e5-com-cache--fallback-determinístico-v29)
  (mergeada como `22627e6` 2026-04-27 manhã). Substitui templates
  determinísticos puros por LLM (LiteLLM + Instructor + Pydantic) com
  cache Redis 24h e fallback determinístico. Toggle global default OFF
  (env `MATHOMS_LLM_SECTION_SUMMARIES=1`) até **v2.9.1** revisar copy
  com [product-designer](.claude/agents/product-designer.md).

  **Decisões fechadas em ADR-144 (Fase 1) — implementadas em Fase 2:**
  - Stack LiteLLM + Instructor + Pydantic (paridade E1/E1.5/E2-llm/E7-review-llm).
  - Cache key `mathoms:llm:section_summary:{workspace_id}:{snapshot_hash}:{section_id}`.
  - TTL 24h. Storage Redis preferido (NoOp se ausente; Postgres+TTL não
    implementado — cobertura atual: Redis ou degrade silencioso).
  - Fallback determinístico via Callable (lê `narrativas.summaries` legado
    do snapshot, ou string genérica por section_id).
  - Telemetry logger `mathoms.llm.section_summaries` (ADR-110), sem PII
    (snapshot_hash truncado a 12 chars; nunca loga texto gerado nem snapshot).
  - Stateless rigoroso (ADR-111): cache Protocol + impls injetadas;
    proibido `lru_cache`/dict global.

  **Estrutura:**
  - `pipeline/llm/schemas/section_summaries.py`: `SectionSummaryOutput`
    Pydantic — `summary_md` (10-400 chars), `tone: Literal["neutral","positive","warning"]`,
    `key_metric_ref?: str`. LLM nunca emite BRL inline (ADR-090); referencia
    métrica via `key_metric_ref` e renderer formata com `<MonetaryValue/>`.
  - `pipeline/domain/services/section_summary_generator.py`:
    `SectionSummaryGenerator` (Protocol-driven — `SectionSummaryLLMClient`,
    `SectionSummaryCache`, `DeterministicFallback Callable`); pipeline
    `cache → LLM → fallback`; `SectionSummaryGeneratorConfig` value-object
    frozen (não recebe `StageConfig` — ADR-097 D2/D3); `SectionSummaryResult`
    com `source: Literal["llm","cache","fallback"]`, `latency_ms`,
    `cost_usd: Decimal` (ADR-090). Telemetria via `_TelemetryEvent` dataclass
    tipado (ADR-097 D1, sem strings ad-hoc).
  - `backend/app/services/llm_cache.py`: `LLMCacheBackend` Protocol;
    `RedisLLMCache` (reusa singleton de `events.py`, falha aberta);
    `NoOpLLMCache`; `InMemoryLLMCache` (apenas tests); helper
    `build_section_summary_cache_key`. Distinto de `ArtifactStore`
    (ADR-127/128) — artefatos têm lineage; cache LLM é runtime efêmero.
  - `backend/app/services/section_summary_orchestrator.py`:
    `_LiteLLMSectionSummaryClient` adapter sobre `pipeline.llm.LLMService`;
    `build_default_generator` wires LiteLLM (Anthropic via env) + Redis
    cache + fallback; `generate_all_section_summaries` itera
    `SUPPORTED_SECTION_IDS` (S1/S2/S3/S4/S7/S8/S9/S10 + T2/T3/T5 + U1/U2 = 13);
    `compute_snapshot_hash` SHA-256 com sort_keys (cache key isola
    seções diferentes do mesmo snapshot — ADR-144 §2).
  - `config/prompts/section_summaries.yaml`: `system_prompt` compartilhado
    + 13 `user_prompt` templates por section_id. Copy editorial é
    placeholder; v2.9.1 abre revisão pelo product-designer.
  - `scripts/e5n_narrativas.py::main_with_store`: hook
    `_e5n_generate_section_summaries(ctx, e5_data)` chama orquestrador
    backend após narrativas determinísticas; persiste
    `e5_data["section_summaries"]` quando toggle ON. Falha aberta se
    backend indisponível (CLI standalone).
  - `frontend/src/lib/api/reports.ts`: `ReportAnalysisData` ganha
    `section_summaries?: Record<string, string>`.
  - `frontend/src/components/report/utils/conclusionUtils.ts`:
    `deriveSectionSummary` prefere `data.section_summaries[id]` quando
    presente e não-vazio; senão cai no template determinístico (rede
    de segurança quando LLM falha ou está OFF).

  **Goldens (sem bater Anthropic em CI):**
  - `tests/test_section_summary_generator.py` (10 testes) — 6 cenários
    do prompt (LLM success, cache hit, timeout, rate limit HTTP 429,
    invalid JSON, cache write→read entre chamadas) + 4 extras (template
    missing, cost_usd Decimal Haiku 4.5 pricing $1/M in + $5/M out,
    cache key formato canônico ADR-144, `SectionSummaryOutput` rejeita
    tone inválido).
  - `tests/test_section_summary_orchestrator.py` (8 testes) — toggle
    env default OFF, generator injetado, snapshot_hash determinístico
    (sort_keys), drift YAML↔código, fallback paths legacy/genérico/None.
  - `tests/fakes/llm.py` — fakes nomeados (CLAUDE.md §Testes "não
    MagicMock"): `FakeLLMSuccess`, `FakeLLMRaisingClient`,
    `make_fake_fallback`. Cobre TimeoutError, RuntimeError com "429",
    ValueError com "pydantic validation error".
  - `frontend/tests/components/report/dataAdapters.test.ts` — 3 testes
    novos (LLM presente, ausente, whitespace).

  **Boundary preservado:** generator não importa
  `redis`/`fastapi`/`celery`/`sqlalchemy` (`dev/check_pipeline_boundaries.py`
  verde). Redis client wire-up vive em `backend/app/services/`. Generator
  recebe Protocol + Callable via construtor.

  **Custo estimado real (refino ADR-144 §5 com pricing 2026-04 vigente):**
  - Haiku 4.5: $1.00/M input + $5.00/M output → 13 seções × (2k in + 500 out)
    = 26k tokens in + 6.5k tokens out = $0.026 + $0.0325 = **~$0.0585 por
    relatório novo**. Com cache hit ratio 60% (TTL 24h, mesmo dia): **~$0.023
    amortizado por relatório**. Para 1000 relatórios/mês = **$23-58/mês**
    (vs $18-54 da estimativa ADR-144 §5 que usava 10 seções; v2.9 entrega
    13 seções — drift +30% vs ADR mas ainda dentro do envelope aceito).
  - Sonnet 4.6 opt-in (`MATHOMS_LLM_SECTION_SUMMARY_MODEL=claude-sonnet-4-6`):
    $3/M in + $15/M out → ~$0.176 por relatório novo, ~$0.070 amortizado.
    Cap mensal: $5/workspace (alarme em telemetria — não implementado em
    Fase 2; lane futura junto com tier upgrade Anthropic).

  **Não entregue (escopo da Fase 2 declarado):**
  - Provisionamento de Redis (assumido pré-existente; reusa singleton de
    `events.py`; degrada para NoOp).
  - Ativação em prod — requer v2.9.1 (revisão de copy) + flip do env em
    deploy.
  - Cap mensal por workspace ($5 alarme) — telemetria registra `cost_usd`
    por chamada; agregação fica para lane futura.
  - Postgres+TTL fallback de cache (ADR-144 §2) — não necessário em deploy
    atual com Redis garantido.

  Hashes: `5a1142d` (C1 generator+cache+schema+prompts) · `c0a79df` (C2
  E5.N integração+orquestrador+adapter LiteLLM) · `d2b1827` (C3 frontend
  prefer-snapshot) · `93992c5` (C4 testes 18 backend + 3 frontend).
