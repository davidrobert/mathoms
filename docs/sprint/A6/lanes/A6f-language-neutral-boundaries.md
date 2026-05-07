---
id: A6f
type: lane
title: "Language-neutral boundaries (ADR-102, R18-R20)"
sprint: A6
status: shipped
adrs: ["[[ADR-109]]", "[[ADR-110]]", "[[ADR-111]]", "[[ADR-112]]"]
depends_on: []
parallel_with: []
tags:
  - type/lane
  - sprint/a6
  - status/shipped
---


# A6f — Language-neutral boundaries (ADR-102, R18-R20)


| # | Sub-fase | Entrega | Esforço | Status |
| --- | --- | --- | --- | --- |
| A6f.1 | Pipeline-as-service | ✅ `pipeline-service/` FastAPI standalone (app + contracts + services); 3 rotas (`POST /runs`, `POST /stages/{stage}/execute`, WS `/events/{run_id}`); `PipelineServiceClient` Protocol + `HttpPipelineClient` + `InProcessPipelineClient`; backend `pipeline_task.py` zero `from pipeline.orchestrator` imports; `docker-compose.pipeline-service.yml`; `/health` do backend reporta `pipeline_service_url`/`reachable`; OpenAPI snapshot em `docs/reference/api/v1/pipeline-service.openapi.json`; 21 tests novos (13 service + 8 client). ADR-112. Extração de helpers de `pipeline_task.py` para ≤100 linhas **deferida** para slice próprio. | 3 sessões | ✅ 2026-04-21 |
| A6f.2 | OpenAPI + codegen | ✅ ~12 DTOs novos; snapshot em `docs/reference/api/v1/openapi.json` (12856 linhas); `make update-openapi-snapshot`; teste estrutural + snapshot diff | 1 sessão | ✅ 2026-04-20 |
| A6f.3 | Structured logs JSON + OTel | ✅ `MathomsJsonFormatter` + `CorrelationIdMiddleware` (trace_id/workspace_id/user_id/pipeline_run_id via contextvars); `setup_otel()` opt-in via `OTEL_EXPORTER_OTLP_ENDPOINT`; FastAPI+SQLAlchemy+Celery instrumentation fork-safe; 8 tests em `test_structured_logging.py`; env vars `MATHOMS_LOG_LEVEL`, `MATHOMS_LOG_FORMAT`; ADR-110 | 1 sessão | ✅ 2026-04-20 |
| A6f.4 | DB schema language-neutral | ✅ `docs/reference/DB_SCHEMA_REFERENCE.md` auto-gerado (27 tabelas, 1193 linhas); `dev/generate_db_schema_reference.py` determinístico; snapshot test + `make update-db-schema-reference`; auditoria zero `PickleType` e zero `DateTime` naive; Go struct tags equivalentes | 1 sessão | ✅ 2026-04-20 |
| A6f.5a | Auth portability documentada | JWT HS256 `{sub, exp, tv}` + Fernet mantidos; ADR-109; `test_auth_portability.py` (12 testes JWT+Fernet parity) | 1 sessão | ✅ 2026-04-20 |
| A6f.5b | Fernet → AES-GCM (deferido) | AES-256-GCM + HKDF-SHA256; migration de `LLMConfig.api_key_encrypted` + vault_entries; decrypt fallback para Fernet durante cutover | 1 sessão | ⏸️ deferido (ADR-109) |
| A6f.5c | JWT HS256 → RS256 (deferido) | Só se houver separação real entre emissor e validador (ex: pipeline-service valida tokens do backend) | 1 sessão | ⏸️ deferido (ADR-109) |
| A6f.6 | Stateless rigoroso | WebSocket via Redis pub/sub; rate limiting Redis; zero `@lru_cache` mutable; `tests/integration/test_multi_worker_concurrency.py` | 1-2 sessões | ✅ 2026-04-20 · ADR-111 · audit em `docs/reference/STATELESS_AUDIT.md` (gaps críticos: 0) + 5 tests multi-worker empíricos. Nenhum refactor de código necessário — backend já era multi-worker-safe desde P5 (WS pub/sub + DB rate limit + zero `asyncio.create_task`). Regra operacional R19 formalizada em CLAUDE.md. |

**Estimativa total A6f:** 6-8 sessões grandes (A6f.5b e .5c só contam se gatilho acionar).

**Gatilhos para A6f.5b (Fernet → AES-GCM)**, qualquer um:
- Requisito de compliance (SOC 2 type II, ISO 27001 exigindo AEAD moderno).
- Migração Go real em curso (aproveita janela de re-encrypt).
- CVE publicado contra Fernet format ou `cryptography.fernet`.

**Gatilho para A6f.5c (JWT RS256)**:
- Separação real entre emissor e validador (ex: A6f.1 pipeline-service
  validando tokens emitidos pelo backend) — até lá HS256 é suficiente.
