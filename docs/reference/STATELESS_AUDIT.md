# Stateless-readiness audit (A6f.6)

**Data:** 2026-04-20 (snapshot inicial) · **Last verified:** 2026-08-03 ([[ADR-359]]: §1/§5/§6 deixam de contar ocorrências à mão e passam a apontar para `dev/check_stateless_primitives.py`; a afirmação anterior de §5 era falsa desde a publicação)
**Escopo:** `backend/app/` + `backend/app/tasks/` + `pipeline/`
**Objetivo:** avaliar se a stack atual sobrevive a `N` uvicorn workers + `M`
Celery workers apontando para o mesmo Postgres + Redis — critério de aceite
para horizontal scale ([[ADR-102]] R19).

---

## Sumário executivo

- **Multi-worker-safe?** ✅ **Sim, sem ressalvas** (pós-[[ADR-212]]; ver §6).
- **Gaps críticos:** 0.
- **Gaps nice-to-have:** 0 (nenhum workaround urgente). Workaround documentado
  para `_PLAYWRIGHT_AVAILABLE` (cache de capability check) apenas por
  clareza — já é idempotente cross-worker.

A maior parte da base **já segue o padrão stateless-ready**: WebSockets
via Redis pub/sub (nada em memória), rate limit de invitations via DB,
ausência das primitivas proibidas ([[ADR-111]] §3) **enforçada por
`dev/check_stateless_primitives.py`** em vez de contada à mão, singletons são
*lazy-init immutable* (cada worker inicializa o seu, operam independentes).

> **Nota de método ([[ADR-359]], 2026-08-03):** este documento afirmou por 3,5
> meses "zero `threading.Thread` em app code" enquanto
> `pipeline_service._start_fallback_thread` existia. Contagem escrita à mão
> registra o momento em que foi escrita, não um invariante. §1, §5 e §6 agora
> delegam ao gate; §2 (globais mutáveis) segue manual, pela razão da
> alternativa 2 da [[ADR-111]].

---

## Catálogo detalhado

### 1. `@lru_cache` / `@functools.cache` / `cached_property`

**Enforçado por** `dev/check_stateless_primitives.py` (hard-fail, `pre-commit`):
decorator de cache em `backend/app/**` ou `pipeline/**` falha o commit. Exceções,
se algum dia houver, vivem na allowlist do gate — e o próprio gate exige que o
path de cada entrada apareça neste documento.

`functools.partial` em `services/documents/document_canonical_rename.py` e
`services/documents/document_reclassify_bulk_service.py` é uso local, não cache —
fora do escopo do gate.

**Veredito:** ✅ OK — nenhum cache mutável cross-request.

### 2. Globais de módulo mutáveis

Levantamento do que existe em `backend/app/**/*.py` atribuído no topo
do módulo (grep `^_[A-Z_]+` e `^[A-Z][A-Z_]+:`):

| Arquivo | Nome | Tipo | Veredito |
|---|---|---|---|
| `services/pipeline/retry_config.py:44` | `STAGE_RETRY_CONFIGS` | `dict[str, StageRetryConfig]` frozen | ✅ imutável (criado uma vez, lido) |
| `services/classification/institution_classifier.py:11` | `INSTITUTION_CONTENT_PATTERNS` | `list[tuple[re.Pattern, str]]` | ✅ regex compilado, nunca alterado (re-exportado por `documents/content_classifier.py`) |
| `services/classification/period_extractor.py:7-27` | `_PERIOD_RANGE_RE`, `_YYYYMM_RE`, `_MONTH_YEAR_BR_RE`, `_MESES` | regex + mapping | ✅ imutável |
| `services/tarefas_md_parser.py:20-146` | `_MD_TO_CATEGORY`, `_MONTH_PT`, `_STATUS_FROM_MD`, `_*_RE` | mapping + regex | ✅ imutável |
| `services/feature_flags_service.py:32` | `DEFAULTS` | `dict[str, bool]` | ✅ imutável (defaults, nunca escritos) |
| `services/task_notification_service.py:25` | `_SOURCE` | `str` | ✅ imutável |
| `services/storage/__init__.py:27` | `_MAGIC_SIGNATURES` | `dict[str, tuple[bytes, ...]]` | ✅ imutável |
| `services/documents/canonical_routing.py:11` | `_MIME_TO_EXT` | `dict[str, str]` | ✅ imutável |
| `services/task_progress_service.py:57-61` | `_BRL_RE`, `_SHORT_BRL_RE` | regex | ✅ imutável |
| `services/documents/document_classification.py:20-30` | `_CONTENT_CONFIDENCE_THRESHOLD`, `_REVIEW_CONFIDENCE_THRESHOLD`, `_TRANSIENT_ERROR_NAMES`, `_PERMANENT_ERROR_NAMES` | thresholds + frozensets | ✅ imutável |
| `services/pipeline/pipeline_adapter.py:409` | `_GOAL_TYPE_MAP` | `dict` | ✅ imutável |
| `services/task_attachment_service.py:29` | `_SUBDIR` | `str` | ✅ imutável |
| `services/pdf_renderer.py:30` | `_PLAYWRIGHT_AVAILABLE` | `Optional[bool]` lazy | ⚠️ mutável mas **idempotente** — cada worker descobre o mesmo resultado independente |
| `services/security/rate_limit.py:41` | `_DEFAULT_POLICIES` | `dict[str, RateLimitPolicy]` (frozen dataclasses) | ✅ categoria (a) — políticas imutáveis; o **contador** vive no Redis (`INCR`+`EXPIRE`, W4-T04 · #720), nunca em memória |
| `services/pdf_renderer.py` (W1-T04 · 2026-05-06) | `_pdf_semaphore` | `asyncio.Semaphore \| None` lazy | ✅ categoria (b) — recurso **local** ao worker (concorrência intra-process), não estado de negócio. Cada worker cria seu Semaphore lendo `settings.MATHOMS_PDF_CONCURRENCY` (mesmo valor → mesmo cap). Não acumula entre requests; protege RAM do Chromium contra OOM em CX32 (8GB). |
| `services/pipeline/events.py:22` | `_redis_client` | Redis connection lazy singleton | ✅ pattern aceito — cada worker tem sua conexão para o Redis compartilhado |
| `services/security/vault.py:77` | `_singleton` | `VaultService` lazy singleton | ✅ mesma lógica — cada worker inicializa o seu, interop zero necessário |
| `core/database.py:52` | `engine` | `AsyncEngine` module-level | ✅ SQLAlchemy pool; cada worker tem seu pool para o DB compartilhado |
| ~~`pipeline/adapters/file_config_store.py`~~ | ~~`FileConfigStore._cache`~~ | ~~`dict[str, Any]` por instância~~ | ✅ **removido em Sprint A7.5** (commit `5d1cf7a` · ADR-134) — produto roda 100% DB-first via `DBConfigStore` |
| `pipeline/domain/lineage_registry.py:26` | `LINEAGE_RULE_REFS` | `dict[str, dict[str, str]]` literal eager | ✅ categoria (a) — mapping de domínio imutável (ADR-281 B2, bridge nó-de-lineage → código); refactor-safe via `dev/check_lineage_refs.py` |
| `pipeline/llm/response_cache.py` (ADR-307 · W6-T02) | cache de resposta LLM | Redis via `WorkspaceContext.llm_response_cache` | ✅ categoria (b) — estado vive no Redis compartilhado (`mathoms:llm:resp:*`, TTL 7d); o pipeline só carrega o Protocol injetado (mesmo padrão `llm_call_hooks`); `NoOpLLMCache` degrada em miss quando Redis cai |
| `core/llm_metrics.py:107` (A33.l7 · ADR-110) | `_EMITTER_SINGLETON` | `OtelLLMMetrics` lazy singleton | ✅ categoria (b) — mesma env (`OTEL_EXPORTER_OTLP_ENDPOINT`) produz o mesmo emitter em qualquer worker; instrumentos OTel são thread-safe por contrato do SDK e o agregado vive no collector, não no processo. Sem endpoint → `None` (no-op, opt-in ADR-110) |

**Veredito:** ✅ **OK**. Todos os globais são (a) constantes imutáveis —
safe; ou (b) singletons idempotentes inicializados lazy — cada worker
inicializa o seu independente, sem interop cross-worker necessário.
Nenhum dict global acumula estado entre requests.

### 3. WebSocket sessions — **Redis pub/sub nativo**

`backend/app/api/ws.py` (31 linhas, router fino) delega para
`application/realtime/pipeline_progress.py` (pub/sub em
`stream_pipeline_progress`) — **já está stateless-ready desde o P5**:

- Nenhuma `set[WebSocket]` ou `dict[run_id, list[WebSocket]]` local.
- Cada conexão abre sua própria `redis.asyncio.Redis.from_url(...)` + `pubsub()`.
- Subscribe ao canal `pipeline:{run_id}` — publisher é o Celery worker
  (`services/pipeline/events.py` `publish_event`).
- **Qualquer uvicorn worker** pode receber a conexão; **qualquer Celery
  worker** pode publicar eventos; o Redis é o único ponto de coordenação.

**Canais em uso:**

- `pipeline:{run_id}` — eventos de pipeline run (stage_started,
  stage_completed, stage_failed, stage_skipped, stage_activity,
  needs_review, run_completed, run_failed, run_cancelled, heartbeat).

**Veredito:** ✅ **OK — já stateless**. Nenhum refactor necessário.
A decisão de sobrepor publisher (Celery) e subscriber (uvicorn) só pelo
Redis é o padrão documentado em ADR-102 R19.

### 4. Rate limiting — **DB-backed + Redis-backed**

Dois mecanismos, ambos sem estado em memória:

- **Invitations (DB):** `MAX_PENDING_PER_WORKSPACE = 10` convites
  pendentes por workspace (`services/invitation_service.py:50`). Check
  via `_count_pending(db, workspace_id, now)` — query Postgres direta.
- **Genérico (Redis, W4-T04 · #720, 2026-07-02):** `services/security/rate_limit.py`
  — janela fixa via `INCR`+`EXPIRE` no Redis compartilhado, políticas por
  scope (login/upload/pipeline_run) em `_DEFAULT_POLICIES` (imutável, §2).
  Falha aberta se Redis indisponível; nenhum token bucket em memória.

**Veredito:** ✅ **OK — Postgres/Redis são o único estado**. Multi-worker
seguro por construção.

### 5. Background tasks — **enforçado, não contado**

`asyncio.create_task`, `fastapi.BackgroundTasks` e `threading.Thread` em
`backend/app/**` + `pipeline/**` são **hard-fail** em
`dev/check_stateless_primitives.py`. Trabalho assíncrono vai pelo Celery
(`backend/app/tasks/`), que usa Redis como broker + backend de resultado —
cross-worker seguro por design.

**Fora do escopo do gate, por decisão:** `threading.Lock` / `threading.Semaphore`
/ `asyncio.Semaphore` sobre objeto **local ao processo** (ex.: `_pdf_semaphore`
em §2, o lock de contador de progresso em `pipeline/stages/extract_with_llm.py`).
Concorrência intra-processo sobre recurso local é categoria (b), não estado de
negócio compartilhado; a [[ADR-111]] §3 nunca as proibiu.

**Histórico ([[ADR-359]]):** esta seção afirmava "`threading.Thread` — nenhum
resultado em app code" desde 2026-04-20 e a afirmação era falsa —
`pipeline_service._start_fallback_thread` (fallback in-process quando o broker
recusava o dispatch) existia desde 2026-04-14 e só foi removido em 2026-08-03.
O thread também não sobrevivia a processo de vida curta, o que produzia run
órfão em `pending`; a decisão de fazer a falha de dispatch ser alta está na
[[ADR-359]].

**Veredito:** ✅ **OK — sustentado por gate**.

### 6. File locks — **enforçado, não contado**

`fcntl`, `flock`, `filelock` e `portalocker` em `backend/app/**` + `pipeline/**`
são hard-fail em `dev/check_stateless_primitives.py`. Nenhum lock em disco que
precisaria ser migrado para advisory lock Postgres ou `SET NX` Redis.

**Status pós-[[ADR-212]] (2026-05-14):** artifacts gravados exclusivamente via
SQLAlchemy + Postgres em `pipeline_artifacts`. `DiskArtifactStore` foi
deletado, flag `MATHOMS_USE_DB_ARTIFACTS` + coluna
`workspaces.use_db_artifacts_override` removidas — classe de risco de escrita
concorrente em disco **eliminada por construção**. Semântica Celery
(`task_acks_late=True` + `task_reject_on_worker_lost=True`) garante 1 worker
por run_id.

**Veredito:** ✅ **OK — DB-only elimina classe de risco**.

### 7. `contextvars` — **request-scoped apenas**

Introduzidos pela A6f.3 em `middleware/correlation.py`:

- `_trace_id`, `_workspace_id`, `_user_id`, `_pipeline_run_id`.

Não há set/reset em escopo de módulo. Middleware Starlette cria token
por request e solta no `finally`. Celery task idealmente chama
`set_pipeline_run_id(run.id)` no início do `run()` — não foi
formalizado ainda mas é recomendação da regra operacional no CLAUDE.md.

**ADR-273 (pipeline):** `pipeline/observability/context.py` adiciona
`_trace_id`, `_workspace_id`, `_run_id`, `_stage` (exceção ADR-111 §1.b,
idêntica ao backend). Pattern obrigatório: `bind()` retorna `BindTokens`
e a Celery task (`pipeline_task`) faz `reset(tokens)` em `finally` —
sem o reset, o contextvar sobrevive à task no worker prefork e o run
seguinte logaria workspace de outro tenant. `_stage` tem set/reset por
stage no orchestrator (`set_stage`/`reset_stage`). Handler de log é
singleton lazy idempotente (`_ensure_handler`, exceção §1.b).

**Veredito:** ✅ **OK**.

### 8. `settings` — `pydantic-settings` singleton imutável

`backend/app/core/config.py` usa pydantic-settings. `settings` é criado
uma vez no módulo; não há mutação em runtime em código da aplicação.

A única mutação existe em `backend/tests/conftest.py:62`
(`settings.FERNET_KEY = _TEST_FERNET_KEY`) — **test-only**, antes do
app lifespan, para compat com runs sem env.

**Veredito:** ✅ **OK**.

### 9. Celery globals — **nenhum dict de estado por run**

`backend/app/worker.py` (102 linhas) e `backend/app/tasks/pipeline_task.py`
(auditado via grep) não declaram `dict`/`list` globais que acumulem estado.
State de um run vive em:

- `PipelineRun` row no Postgres (status, current_stage, paused_at_stage).
- `pipeline_artifacts` rows (outputs).
- `celery_task_id` em `PipelineRun` (controle de cancelamento).

**Veredito:** ✅ **OK**.

### 10. Vault caching

`services/security/vault.py:77` — `_singleton: VaultService | None = None` +
`get_vault()` lazy. Cada worker inicializa seu `VaultService` (que
lê `settings.FERNET_KEY` — mesmo valor em todos os workers). Encrypt/
decrypt é determinístico sobre a mesma key.

**Veredito:** ✅ **OK**.

---

## Gaps e ações

**Gaps críticos:** 0.

**Gaps secundários:** 0.

**Observações documentacionais** (não exigem código):

- 🟢 **§5 Bg tasks**: a proibição de `asyncio.create_task` está informal;
  poderia virar regra operacional explícita no CLAUDE.md ("background
  work sempre via Celery"). Adicionada na A6f.6 junto com nova ADR.
- 🟢 **§3 WS**: teste integrado multi-worker **ainda não existe**. Este é
  o entregável nuclear da A6f.6 — valida empiricamente que o que o audit
  diz no papel funciona na prática. Vai em
  `tests/integration/test_multi_worker_concurrency.py`.
- 🟢 **§6 File locks**: risco residual eliminado — default
  `MATHOMS_USE_DB_ARTIFACTS=True` a partir de 2026-04-23 (ADR-118).

---

## Critério de aceite

Rodar 2 uvicorn workers + 2 Celery workers apontando para o mesmo
Redis + Postgres:

| Cenário | Comportamento esperado |
|---|---|
| Login em worker A, acessar `/api/*` em worker B com o token | JWT validado em ambos (HS256 + mesma `SECRET_KEY`) |
| Abrir WS em worker A, Celery task em worker C publica evento | Cliente recebe evento via Redis pub/sub |
| Upload em worker A, fetch `/documents` em worker B | Doc aparece (estado é Postgres) |
| Rate limit de invitations: tentar 11x em workers alternados | 11º é bloqueado (contagem Postgres) |
| Worker A morre durante request | Requests em worker B continuam; Celery tasks em andamento reenfileiram (`task_reject_on_worker_lost=True`) |

**Teste de integração** cobre os 4 primeiros cenários.
Cenário 5 (fail-over) é manual — runbook em `docs/reference/RUNBOOK.md`.

---

**ADR associado:** ADR-111 (próxima a ser registrada — gaps zero = ADR
reflete o audit + formaliza o padrão para novos módulos).

| `events.Publisher.client` (Go, `services/pipeline-service-go/internal/events/publisher.go`) | (b) singleton lazy idempotente | Client Redis do publisher de eventos — mesma key (REDIS_URL) produz mesmo client; best-effort, falha não derruba run (F1 Fase 3, decisão 11 do track f1-go-service) |
