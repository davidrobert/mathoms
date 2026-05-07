---
id: ADR-110
type: adr
title: "Structured JSON logging + OpenTelemetry bootstrap (A6f.3)"
status: Decidido
date: "2026-04-20"
relates_to: []
supersedes: []
superseded_by: []
aliases: ["ADR 110"]
tags:
  - area/backend
  - area/observability
  - area/persistence
  - phase/a6f-3
  - status/decidido
  - type/adr
size_lines: 133
---

# ADR-110 — Structured JSON logging + OpenTelemetry bootstrap (A6f.3)

**Status:** Decidido • **Data:** 2026-04-20 • **Plano:** §19 A6f.3

**Contexto:** A6f.3 pede logs estruturados + tracing cross-service. Sem isso,
qualquer investigação em produção exige grepar linhas de texto livre e
correlacionar manualmente request → task → DB query. Se um dia o pipeline
migrar para Go (cenário A6f.1), manter o contrato de observabilidade em
formato neutro (JSON + OTLP) é obrigatório — binding a um agente específico
(Sentry SDK, DataDog tracer) amarra todos os serviços à mesma linguagem.

Três dimensões:

1. **Formato de log**: texto humano (status atual) vs. JSON. JSON é
   jq-compatível, parseável por qualquer log aggregator (Loki, Elasticsearch,
   CloudWatch Insights), e obrigatório se múltiplos serviços (API, worker,
   pipeline-service) gravam no mesmo stream.
2. **Correlation IDs**: trace_id precisa fluir request → Celery task → DB
   query → log line. Opções: (a) thread-locals (quebra em async), (b)
   contextvars (Python 3.7+ oficial, seguro em asyncio + threads),
   (c) OpenTelemetry context propagation (trace API). Escolha canônica:
   contextvars próprios (baseline) + OTel trace context (quando habilitado),
   ambos injetados nos log records.
3. **Tracing**: instrumentação opt-in via OTLP. Habilitar só quando
   `OTEL_EXPORTER_OTLP_ENDPOINT` estiver no env — evita custo de rede
   em dev e em workspaces sem collector.

**Alternativas consideradas:**

- **Apenas logs de texto + grep** — inviável cross-service; regex frágil.
- **Sentry SDK para tudo** — vendor lock-in, custo por volume; não cobre
  traces no formato OTLP neutro.
- **Logfmt em vez de JSON** — menor overhead, mas jq não parse nativamente
  e campos aninhados (ex.: `extra={"custom": {"nested": "ok"}}`) ficam
  serializados como strings.
- **FastAPIInstrumentor + SQLAlchemyInstrumentor sempre ligados** — custo
  de CPU em testes e dev quando nenhum backend está escutando. Só liga em
  `setup_otel()` se o endpoint OTLP estiver setado; `LoggingInstrumentor`
  liga sempre (custo desprezível, mas popula `otelTraceID`/`otelSpanID`
  nos log records).

**Decisão:**

1. **Formato padrão: JSON** (`python-json-logger` `JsonFormatter`).
   Feature flag `MATHOMS_LOG_FORMAT=text` volta para formatter humano com
   sufixo `[trace=XXXXXXXX]` quando há correlation id — útil em REPL e
   debugging local.
2. **Correlation context via contextvars próprios** em
   `backend/app/middleware/correlation.py`:
   - `_trace_id` (UUID v4, auto-gerado ou lido do header `X-Trace-Id`)
   - `_workspace_id` (setado pelo dispatcher quando conhecido)
   - `_user_id` (setado pelo dispatcher quando conhecido)
   - `_pipeline_run_id` (setado pela Celery task quando dentro de um run)
3. **MathomsJsonFormatter** injeta todos os 4 IDs + `timestamp` (UTC ISO
   8601 com `Z`) + `level` + `logger` + `otelTraceID`/`otelSpanID` (quando
   presentes via `LoggingInstrumentor`).
4. **`CorrelationIdMiddleware`** (Starlette): gera/lê `X-Trace-Id` no
   request, reflete no header da response, emite contextvar token.
5. **`setup_otel(service_name)`** idempotente via `_INSTRUMENTED`.
   `LoggingInstrumentor` sempre liga (popula trace context em records);
   `OTLPSpanExporter` só liga se `OTEL_EXPORTER_OTLP_ENDPOINT` estiver
   setado. Falha silenciosa (warning) se exporter não consegue inicializar
   — observabilidade nunca derruba a API.
6. **`instrument_fastapi(app)`** chamado no lifespan, antes de
   `init_db()`. Instala `FastAPIInstrumentor` + `SQLAlchemyInstrumentor`.
7. **`instrument_celery()`** chamado em `worker_process_init` signal —
   fork-safe; cada worker process reinicializa SDK + handlers.
8. **Namespace `mathoms.*`** para loggers de aplicação (`get_logger("api.foo")`
   vira `mathoms.api.foo`). Permite filtrar nossos logs dos de terceiros
   (uvicorn, sqlalchemy, celery).
9. **Idempotência**: `setup_logging()` marca o handler com atributo
   `_mathoms_managed = True` e remove duplicatas. Chamar N vezes (tests,
   lifespan, celery init) não acumula handlers.

**Contratos a manter:**

- Todo log line é JSON autocontido (uma linha = um objeto JSON válido).
  Enforçado por `test_json_lines_are_jq_compatible` — cada linha
  `json.loads()` limpo.
- Quando o contextvar está setado, o campo aparece no JSON. Quando não
  está, o campo é omitido (não vira `"trace_id": null`) — reduz ruído.
- `X-Trace-Id` é reflexivo: header de entrada preservado; senão, gerado
  como UUID v4 e devolvido. Cross-service ganha propagation grátis desde
  que o cliente envie o header.
- OTLP endpoint ausente não quebra a app — `is_otel_enabled() == False`
  e `setup_otel` só faz log correlation (sem exporter).

**Consequências:**

- ✅ Logs de API, worker e (futuro) pipeline-service têm mesmo formato,
  mesma semântica de correlation, mesmo shape de trace context.
- ✅ Auditoria post-hoc por `trace_id` resolve via jq/Loki — zero regex
  sobre campos textuais.
- ✅ Migração hipotética para Go mantém contrato — qualquer tracer
  OTLP-compliant interopera.
- ✅ Feature flag `MATHOMS_LOG_FORMAT=text` preserva UX de debugging local.
- ✅ OTLP off-by-default — zero custo em dev.
- ⚠️ Overhead de JSON serialize por log line (desprezível em prática,
  medido <5% em benchmark local).
- ⚠️ `LoggingInstrumentor().instrument(set_logging_format=False)` faz
  monkey-patch global — inofensivo mas obriga reset cuidadoso em testes.
- ❌ Log format atual existente (texto simples) será quebrado para
  consumidores externos; mitigado pelo feature flag text.

**Artefatos:**

- `backend/app/core/logging.py` — formatter + `setup_logging()` + `get_logger()`.
- `backend/app/core/otel.py` — `setup_otel()` + `instrument_fastapi()`
  + `instrument_celery()` + `is_otel_enabled()`.
- `backend/app/middleware/correlation.py` — middleware + contextvars +
  setters/getters.
- `backend/app/main.py` — wire no módulo (`setup_logging`, `setup_otel`)
  + lifespan (`instrument_fastapi`) + `CorrelationIdMiddleware`.
- `backend/app/worker.py` — `@worker_process_init.connect` calls
  `setup_logging` + `setup_otel("mathoms-worker")` + `instrument_celery`.
- `backend/requirements.txt` — `python-json-logger>=3.2`,
  `opentelemetry-api/sdk>=1.30`, `opentelemetry-exporter-otlp-proto-http`,
  `opentelemetry-instrumentation-{fastapi,sqlalchemy,celery,logging}>=0.50b0`.
- `backend/tests/test_structured_logging.py` — 8 tests cobrindo formatter,
  context propagation, middleware, idempotência, OTel opt-in, jq compat.

**Env vars (novas):**

- `MATHOMS_LOG_LEVEL` (default `INFO`) — `DEBUG|INFO|WARNING|ERROR|CRITICAL`.
- `MATHOMS_LOG_FORMAT` (default `json`) — `json|text`. Text é humano com
  `[trace=XXXXXXXX]` quando há correlation id.
- `OTEL_EXPORTER_OTLP_ENDPOINT` (opt-in) — URL do collector. Ausente =
  só correlation nos logs, sem exporter.

**Próxima sub-fase relacionada:** A6f.6 (stateless rigoroso + WS Redis
pub/sub + multi-worker test) — ver §19.6 do plano.
