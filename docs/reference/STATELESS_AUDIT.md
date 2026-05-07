# Stateless-readiness audit (A6f.6)

**Data:** 2026-04-20
**Escopo:** `backend/app/` + `backend/app/tasks/` + `pipeline/`
**Objetivo:** avaliar se a stack atual sobrevive a `N` uvicorn workers + `M`
Celery workers apontando para o mesmo Postgres + Redis — critério de aceite
para horizontal scale (ADR-102 R19).

---

## Sumário executivo

- **Multi-worker-safe?** ✅ **Sim, com uma ressalva operacional menor** (ver §6).
- **Gaps críticos:** 0.
- **Gaps nice-to-have:** 0 (nenhum workaround urgente). Workaround documentado
  para `_PLAYWRIGHT_AVAILABLE` (cache de capability check) apenas por
  clareza — já é idempotente cross-worker.

A maior parte da base **já segue o padrão stateless-ready**: WebSockets
via Redis pub/sub (nada em memória), rate limit de invitations via DB,
zero `asyncio.create_task` fora do Celery, zero file locks, zero
`@lru_cache` em código da aplicação, singletons são *lazy-init immutable*
(cada worker inicializa o seu, operam independentes).

---

## Catálogo detalhado

### 1. `@lru_cache` / `@functools.cache` / `cached_property`

**Resultado:** zero uso em `backend/app/`. O único `from functools import
partial` aparece em `api/documents.py:667` (uso local, não cache).

**Veredito:** ✅ OK — nenhum cache mutável cross-request.

### 2. Globais de módulo mutáveis

Levantamento do que existe em `backend/app/**/*.py` atribuído no topo
do módulo (grep `^_[A-Z_]+` e `^[A-Z][A-Z_]+:`):

| Arquivo | Nome | Tipo | Veredito |
|---|---|---|---|
| `services/retry_config.py:41` | `STAGE_RETRY_CONFIGS` | `dict[str, StageRetryConfig]` frozen | ✅ imutável (criado uma vez, lido) |
| `services/content_classifier.py:33` | `INSTITUTION_CONTENT_PATTERNS` | `list[tuple[re.Pattern, str]]` | ✅ regex compilado, nunca alterado |
| `services/content_classifier.py:457-467` | `_PERIOD_RANGE_RE`, `_YYYYMM_RE`, `_MONTH_YEAR_BR_RE`, `_MESES` | regex + mapping | ✅ imutável |
| `services/tarefas_md_parser.py:20-146` | `_MD_TO_CATEGORY`, `_MONTH_PT`, `_STATUS_FROM_MD`, `_*_RE` | mapping + regex | ✅ imutável |
| `services/feature_flags_service.py:32` | `DEFAULTS` | `dict[str, bool]` | ✅ imutável (defaults, nunca escritos) |
| `services/task_notification_service.py:25` | `_SOURCE` | `str` | ✅ imutável |
| `services/goal_service.py:417` | `_GOAL_TYPE_CLASSES` | `dict[str, tuple[type, ...]]` | ✅ imutável |
| `services/storage.py:27` | `_MAGIC_SIGNATURES` | `dict[str, tuple[bytes, ...]]` | ✅ imutável |
| `services/canonical_routing.py:11` | `_MIME_TO_EXT` | `dict[str, str]` | ✅ imutável |
| `services/task_progress_service.py:32-83` | `_DEFAULT_APORTE_KEYWORDS`, `_BRL_RE`, `_SHORT_BRL_RE` | list + regex | ✅ imutável |
| `services/document_classification.py:20-30` | `_CONTENT_CONFIDENCE_THRESHOLD`, `_REVIEW_CONFIDENCE_THRESHOLD`, `_TRANSIENT_ERROR_NAMES`, `_PERMANENT_ERROR_NAMES` | thresholds + frozensets | ✅ imutável |
| `services/pipeline_adapter.py:153` | `_GOAL_TYPE_MAP` | `dict` | ✅ imutável |
| `services/task_attachment_service.py:29` | `_SUBDIR` | `str` | ✅ imutável |
| `services/pdf_renderer.py:27` | `_PLAYWRIGHT_AVAILABLE` | `Optional[bool]` lazy | ⚠️ mutável mas **idempotente** — cada worker descobre o mesmo resultado independente |
| `services/pdf_renderer.py` (W1-T04 · 2026-05-06) | `_pdf_semaphore` | `asyncio.Semaphore \| None` lazy | ✅ categoria (b) — recurso **local** ao worker (concorrência intra-process), não estado de negócio. Cada worker cria seu Semaphore lendo `settings.MATHOMS_PDF_CONCURRENCY` (mesmo valor → mesmo cap). Não acumula entre requests; protege RAM do Chromium contra OOM em CX32 (8GB). |
| `services/events.py:16` | `_redis_client` | Redis connection lazy singleton | ✅ pattern aceito — cada worker tem sua conexão para o Redis compartilhado |
| `services/vault.py:48` | `_singleton` | `VaultService` lazy singleton | ✅ mesma lógica — cada worker inicializa o seu, interop zero necessário |
| `core/database.py:11` | `engine` | `AsyncEngine` module-level | ✅ SQLAlchemy pool; cada worker tem seu pool para o DB compartilhado |
| ~~`pipeline/adapters/file_config_store.py`~~ | ~~`FileConfigStore._cache`~~ | ~~`dict[str, Any]` por instância~~ | ✅ **removido em Sprint A7.5** (commit `5d1cf7a` · ADR-134) — produto roda 100% DB-first via `DBConfigStore` |

**Veredito:** ✅ **OK**. Todos os globais são (a) constantes imutáveis —
safe; ou (b) singletons idempotentes inicializados lazy — cada worker
inicializa o seu independente, sem interop cross-worker necessário.
Nenhum dict global acumula estado entre requests.

### 3. WebSocket sessions — **Redis pub/sub nativo**

`backend/app/api/ws.py` (99 linhas) **já está stateless-ready desde o P5**:

- Nenhuma `set[WebSocket]` ou `dict[run_id, list[WebSocket]]` local.
- Cada conexão abre sua própria `redis.asyncio.Redis.from_url(...)` + `pubsub()`.
- Subscribe ao canal `pipeline:{run_id}` — publisher é o Celery worker
  (`services/events.py` `publish_event`).
- **Qualquer uvicorn worker** pode receber a conexão; **qualquer Celery
  worker** pode publicar eventos; o Redis é o único ponto de coordenação.

**Canais em uso:**

- `pipeline:{run_id}` — eventos de pipeline run (stage_started,
  stage_completed, stage_failed, stage_skipped, stage_activity,
  needs_review, run_completed, run_failed, run_cancelled, heartbeat).

**Veredito:** ✅ **OK — já stateless**. Nenhum refactor necessário.
A decisão de sobrepor publisher (Celery) e subscriber (uvicorn) só pelo
Redis é o padrão documentado em ADR-102 R19.

### 4. Rate limiting — **DB-backed**

Único rate limit na base: `MAX_PENDING_PER_WORKSPACE = 10` convites
pendentes por workspace (`services/invitation_service.py:50`). Check
via `_count_pending(db, workspace_id, now)` — query Postgres direta,
sem cache local, sem token bucket em memória.

**Veredito:** ✅ **OK — DB é o único estado**. Multi-worker seguro por
construção.

### 5. Background tasks — **zero `asyncio.create_task` / `BackgroundTasks`**

Grep em `backend/app/` — zero uso de:

- `asyncio.create_task(...)` — nenhum resultado.
- `fastapi.BackgroundTasks` — nenhum resultado.
- `threading.Thread` — nenhum resultado em app code.

**Todas** as tarefas assíncronas vão pelo Celery (`backend/app/tasks/`),
que usa Redis como broker + backend de resultado. Cross-worker seguro
por design.

**Veredito:** ✅ **OK**.

### 6. File locks — **zero uso**

Grep `fcntl`, `flock`, `filelock`, `portalocker` em `backend/` e
`pipeline/` — **zero resultados**. Nenhum lock em disco que precisaria
ser migrado para advisory lock Postgres ou `SET NX` Redis.

**Ressalva operacional:** default `MATHOMS_USE_DB_ARTIFACTS=True` (ADR-118,
2026-04-23) — artifacts gravados via SQLAlchemy + Postgres, risco de escrita
concorrente em disco eliminado. Workspaces com
`use_db_artifacts_override=FALSE` (debug) ainda gravam em
`storage/<ws>/processed/...`; a semântica Celery (`task_acks_late=True` +
`task_reject_on_worker_lost=True`) garante 1 worker por run_id mesmo nesse
modo.

**Veredito:** ✅ **OK — default DB elimina classe de risco**.

### 7. `contextvars` — **request-scoped apenas**

Introduzidos pela A6f.3 em `middleware/correlation.py`:

- `_trace_id`, `_workspace_id`, `_user_id`, `_pipeline_run_id`.

Não há set/reset em escopo de módulo. Middleware Starlette cria token
por request e solta no `finally`. Celery task idealmente chama
`set_pipeline_run_id(run.id)` no início do `run()` — não foi
formalizado ainda mas é recomendação da regra operacional no CLAUDE.md.

**Veredito:** ✅ **OK**.

### 8. `settings` — `pydantic-settings` singleton imutável

`backend/app/core/config.py` usa pydantic-settings. `settings` é criado
uma vez no módulo; não há mutação em runtime em código da aplicação.

A única mutação existe em `backend/tests/conftest.py:62`
(`settings.FERNET_KEY = _TEST_FERNET_KEY`) — **test-only**, antes do
app lifespan, para compat com runs sem env.

**Veredito:** ✅ **OK**.

### 9. Celery globals — **nenhum dict de estado por run**

`backend/app/worker.py` (69 linhas) e `backend/app/tasks/pipeline_task.py`
(auditado via grep) não declaram `dict`/`list` globais que acumulem estado.
State de um run vive em:

- `PipelineRun` row no Postgres (status, current_stage, paused_at_stage).
- `pipeline_artifacts` rows (outputs).
- `celery_task_id` em `PipelineRun` (controle de cancelamento).

**Veredito:** ✅ **OK**.

### 10. Vault caching

`services/vault.py:48` — `_singleton: VaultService | None = None` +
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
