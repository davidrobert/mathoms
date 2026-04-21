# Track A6f.1 — Pipeline-as-Service (HTTP boundary)

> **Lane ID:** A6f.1
> **Branch prefix:** `agent/a6f1-pipeline-service/*`
> **Depende de:** A6e per-aggregate ✅ · A6f.2/.3/.4/.5a/.6 ✅ · A6g.1 ✅
> **Paralelo com:** A6g.2 pipeline sweep, A6g.5 tests sweep, A6e.3 use cases (scoped non-pipeline) — zero overlap de arquivos **se** o slice respeitar o escopo abaixo.
> **Conflita com:** qualquer commit ativo em `pipeline/orchestrator.py`, `pipeline/stage_spec.py`, `backend/app/tasks/pipeline_task.py`, `backend/app/api/pipeline.py`, `backend/app/services/events.py`.
> **Onda:** 2 (primeira lane da Onda 2 — greenfield, sem bloqueio de A6e.3/.4)
> **Índice de prompts:** [README.md](README.md)
> **Fonte de verdade:** [CLAUDE.md §Code style](../../CLAUDE.md#code-style), [ADR-102](../DECISIONS.md), [ADR-111](../DECISIONS.md)

> **Objetivo:** criar serviço HTTP standalone `pipeline-service/` que expõe
> execução de stages via FastAPI (`/api/v1/pipeline/runs`,
> `/stages/{stage}/execute`, WS `/events`). Backend passa a consumir
> pipeline-service **por HTTP**, nunca por `import pipeline.*`.
> Esta é a primeira fronteira language-neutral (ADR-102 R18) — prepara
> migração futura para Go sem mudar contrato.

---

## Por que este slice agora

A6e per-aggregate fechou (6 agregados com repo+DTO); A6f.2/.3/.4/.5a/.6
entregaram OpenAPI snapshot, structured logs, DB schema neutro e
stateless rigoroso. O gap restante para a fronteira language-neutral é
**execução de pipeline via import direto**. Hoje:

```python
# backend/app/tasks/pipeline_task.py (exemplo atual)
from pipeline.orchestrator import _run_stage, LLM_STAGES
from pipeline.stage_spec import FULL_ORDER, DETERMINISTIC_ORDER
```

Depois de A6f.1:

```python
# backend/app/services/pipeline_http_client.py
response = await http_client.post(
    f"{PIPELINE_SERVICE_URL}/api/v1/pipeline/stages/E3/execute",
    json={"run_id": run_id, "workspace_root": str(ctx.root)},
)
```

**A6f.1 é Onda 2** mas **não depende de A6e.3/.4** (é greenfield); pode
começar paralelo a A6g.2 e A6g.5 sem merge hell desde que:
- Toca **apenas** a nova pasta `pipeline-service/` na bootstrap.
- **Só** modifica `backend/app/tasks/pipeline_task.py` no último commit
  (cutover HTTP), quando A6g.2 Tier 2 já não estiver ativo.

---

## Regras inegociáveis

Do CLAUDE.md + ADRs:

1. **Pipeline não importa framework** (CLAUDE.md §Regras críticas): `pipeline/**/*.py` não importa `fastapi`/`celery`/`sqlalchemy`. Enforçado por `dev/check_pipeline_boundaries.py`. **Pipeline-service (novo) vive fora do pacote `pipeline/`** — tem permissão de FastAPI, mas importa `pipeline/` como biblioteca read-only.
2. **Stateless rigoroso** (ADR-111): pipeline-service **não tem DB**. Nenhum `@lru_cache` mutable, nenhum counter in-memory entre requests, nenhum `asyncio.create_task`/`BackgroundTasks`. Cache vai para Redis; singletons lazy têm que ser idempotentes em qualquer worker.
3. **Dinheiro nunca é `float`** (ADR-090): qualquer DTO que cruze HTTP carrega string decimal.
4. **Funções 4-20 linhas, arquivos ≤500, nomes específicos** (§Code style).
5. **Structured logs JSON** (ADR-110): pipeline-service herda `MathomsJsonFormatter` + `CorrelationIdMiddleware`.
6. **OpenAPI 3.1 + snapshot** (ADR-109): qualquer endpoint novo → `response_model` explícito + `make update-openapi-snapshot`.
7. **Preserve comentários existentes** em qualquer arquivo refatorado.

---

## Estado atual — arquivos críticos

| Arquivo | Linhas | Função |
|---|---|---|
| `pipeline/orchestrator.py` | 333 | `run_pipeline()`, `run_from()`, `_run_stage()`, `_get_stage_runner()` |
| `pipeline/stage_spec.py` | 221 | `STAGE_REGISTRY` (18 stages), `FULL_ORDER`, `DETERMINISTIC_ORDER`, `VIRTUAL_ARTIFACT_STAGES` |
| `backend/app/tasks/pipeline_task.py` | 628 | Celery task `execute_pipeline_task` — **este é o call-site que vira HTTP client** |
| `backend/app/api/pipeline.py` | 428 | REST handler `/run`, valida `from_stage` via import |
| `backend/app/services/pipeline_service.py` | 219 | `start_pipeline_run()`, `cancel_pipeline_run()` |
| `backend/app/services/events.py` | 134 | Redis Pub/Sub `publish_stage_*`, canal `pipeline:{run_id}` |
| `backend/app/schemas/pipeline.py` | 121 | `PipelineRunRequest/Response`, `PipelineStageLogResponse` — **já REST-native; vira contrato HTTP direto** |
| `backend/app/services/db_artifact_store.py` | 118 | `DBArtifactStore` SQLAlchemy — **permanece no backend** |
| `pipeline/artifact_store.py` | — | Protocolos `ArtifactStore` + `InMemoryArtifactStore` + `DiskArtifactStore` |

**Total refactor direto:** ~2200 linhas. Bem dentro de 2-3 sessões se seguir a sequência abaixo.

---

## Targets — sequência de slices

### Slice 1 — Bootstrap `pipeline-service/` (greenfield, 1 sessão)

**Objetivo:** serviço HTTP rodando standalone, sem ainda substituir call-site backend.

Criar pasta nova `pipeline-service/`:

```
pipeline-service/
  app/
    main.py               # FastAPI app, CorrelationId middleware, JSON logs
    api/
      runs.py             # POST /api/v1/pipeline/runs, GET /runs/{id}
      stages.py           # POST /api/v1/pipeline/stages/{stage}/execute
      events.py           # WS /api/v1/pipeline/events/{run_id}
    contracts/            # Pydantic DTOs — copiar shape de backend/app/schemas/pipeline.py
      runs.py
      stages.py
      events.py
    services/
      stage_executor.py   # wrap pipeline.orchestrator._run_stage — NÃO duplicar lógica
      run_coordinator.py  # sessão longa: orquestra sequência de stages
      event_publisher.py  # Redis pub/sub — reusa schema de backend/app/services/events.py
    config.py             # settings (PIPELINE_SERVICE_URL, REDIS_URL, WORKSPACE_STORAGE_ROOT)
  Dockerfile
  pyproject.toml
  tests/
    test_stage_execution.py    # InMemoryArtifactStore + stage isolado
    test_run_coordinator.py    # mock do orchestrator
    test_events_ws.py          # FakeRedis
```

**Regras:**
- `pipeline-service/app/services/stage_executor.py` **importa** `pipeline.orchestrator._run_stage` — pipeline-service é caller, `pipeline/` é biblioteca. `dev/check_pipeline_boundaries.py` só restringe imports **dentro** de `pipeline/` — ler `pipeline/` de fora é OK.
- **Artifacts via HTTP:** backend envia payload → pipeline-service usa `InMemoryArtifactStore` durante execução → retorna payload → backend persiste em `DBArtifactStore`. Pipeline-service **nunca** fala com DB.
- **Contratos:** copiar shape dos Pydantic em `backend/app/schemas/pipeline.py`. Se 2 DTOs divergirem depois (backend adiciona campo), regenerar OpenAPI.
- **Gate:** `curl http://localhost:8001/api/v1/pipeline/runs` retorna 200 com lista vazia. `pytest pipeline-service/tests -q` verde.

**Commit 1:** `feat(pipeline-service): bootstrap FastAPI standalone (A6f.1 slice 1)`

### Slice 2 — Integração backend via adapter (1 sessão)

**Objetivo:** backend ganha camada HTTP client; permanece com fallback para import direto durante flag.

Criar `backend/app/services/pipeline_client.py`:

```python
class PipelineServiceClient(Protocol):
    async def execute_stage(self, run_id: str, stage: str, ...) -> StageResult: ...
    async def list_runs(self, workspace_id: str) -> list[RunSummary]: ...

class HttpPipelineClient(PipelineServiceClient):
    """Real client — fala com pipeline-service via HTTP."""

class InProcessPipelineClient(PipelineServiceClient):
    """Adapter — chama pipeline.orchestrator._run_stage no mesmo processo.
    Usado em dev/test ou quando MATHOMS_PIPELINE_SERVICE_URL não está setada."""
```

Feature flag `MATHOMS_PIPELINE_SERVICE_URL` (env var, não config):
- **Setada** → `HttpPipelineClient` (cutover real)
- **Não setada** → `InProcessPipelineClient` (dev/test)

`backend/app/tasks/pipeline_task.py` troca imports diretos por `client = get_pipeline_client()` injetado. Logic de stages fica no client — `pipeline_task` vira orchestrator fino (≤100 linhas).

**Regras:**
- Não deletar `pipeline_task` — ele ainda existe, só fica fino.
- Testes existentes (`backend/tests/test_pipeline_task.py`) continuam passando com `InProcessPipelineClient`.
- Novo `test_http_pipeline_client.py` com `httpx.MockTransport` + ciclo `start run → execute stage → stream events`.
- **Gate:** `pytest backend/tests -q` verde com flag desligada; `pytest backend/tests -q` verde com `MATHOMS_PIPELINE_SERVICE_URL=http://mock` + `HttpPipelineClient` mockado.

**Commit 2:** `refactor(backend): PipelineServiceClient adapter + HttpPipelineClient (A6f.1 slice 2)`

### Slice 3 — Smoke + OpenAPI + docker-compose (1 sessão)

**Objetivo:** sistema reproduzível em dev, validado via smoke-up + docker-compose.

- `docker-compose.pipeline-service.yml` adiciona serviço `pipeline-service` na rede do `smoke.yml`.
- `make smoke-up` passa a subir pipeline-service também; `GET /health` do backend reporta `pipeline_service_url` + `pipeline_service_reachable`.
- OpenAPI de pipeline-service gerado: `make update-openapi-snapshot` inclui `docs/api/v1/pipeline-service.openapi.json` (novo).
- `docs/ARCHITECTURE.md §17` (arquitetura alvo pós-A6): adicionar diagrama com pipeline-service HTTP boundary.
- `docs/DECISIONS.md`: ADR-112 (novo) formaliza contrato HTTP + protocolo WS de eventos.

**Gate:**
- `make smoke-up && curl http://localhost:8000/health | jq .pipeline_service_reachable` = `true`.
- `pytest pipeline-service/tests backend/tests tests -q` full verde.
- `make update-openapi-snapshot` sem erro; commit inclui novo snapshot.

**Commit 3:** `infra(pipeline-service): docker-compose + smoke integration + OpenAPI snapshot (A6f.1 slice 3)`

**Commit N+1** (docs hotspot, atomic ≤5min):
- `docs/CHANGELOG.md [Unreleased]`: entrada A6f.1 com 3 slices + impact.
- `docs/BACKLOG.md`: A6f.1 ☐ → ✅ + data; atualiza status global.
- `docs/DECISIONS.md`: ADR-112 link.

---

## O que este slice NÃO toca

- **`backend/app/api/pipeline.py`** (REST) — segue existindo como façade para frontend. Só muda `PipelineService` backend que agora delega para `PipelineServiceClient`.
- **`backend/app/services/db_artifact_store.py`** — stateless rigoroso exige que pipeline-service não tenha DB; DBArtifactStore fica só no backend. Fluxo: backend lê artifact → passa payload para pipeline-service → recebe resultado → escreve.
- **Stages LLM** (E1, E1.5, E2-llm, E7-review) — mesma execução; pipeline-service só expõe HTTP, lógica interna inalterada.
- **Celery worker** — continua existindo; Celery task passa a chamar HTTP client em vez de import direto.
- **Migration real para Go** — escopo de sprint futuro (A6f seguinte); A6f.1 deixa **o contrato** pronto, não a implementação.

---

## Sequência de execução

### 1. Setup

```bash
git fetch origin
git worktree list            # confirma zero worktree em agent/a6f1-*
git for-each-ref --sort=-committerdate \
  --format='%(committerdate:iso) %(refname:short)' \
  refs/remotes/origin/agent/ | head -15
git checkout -b agent/a6f1-pipeline-service/$(date +%Y%m%d-%H%M)
```

### 2. Baseline

```bash
pytest tests -q 2>&1 | tail -3
pytest backend/tests -q 2>&1 | tail -3
make update-openapi-snapshot && git diff --stat docs/api/
# anotar baseline; qualquer falha nova pós-refactor = rollback
```

### 3. Slices na ordem acima — gate após cada um

### 4. Gates de push

```bash
pre-commit run --all-files
pytest pipeline-service/tests -q
pytest backend/tests -q                 # com e sem MATHOMS_PIPELINE_SERVICE_URL setada
pytest tests -q                         # pipeline package intacto
make update-openapi-snapshot && git diff docs/api/

# Drift check antes de push
git fetch origin
BEHIND=$(git rev-list --count HEAD..origin/main)
[ "$BEHIND" -gt 0 ] && git rebase origin/main && pytest backend/tests -q

git push origin HEAD:main
```

---

## Critérios de aceite (binários)

- [ ] Pasta `pipeline-service/` existe com FastAPI app iniciável (`uvicorn pipeline-service.app.main:app`).
- [ ] Endpoints `POST /api/v1/pipeline/runs`, `POST /api/v1/pipeline/stages/{stage}/execute`, WS `/api/v1/pipeline/events/{run_id}` respondem.
- [ ] `PipelineServiceClient` Protocol + 2 implementações (`HttpPipelineClient`, `InProcessPipelineClient`) em `backend/app/services/pipeline_client.py`.
- [ ] `backend/app/tasks/pipeline_task.py` ≤100 linhas; `grep "from pipeline.orchestrator" backend/app/tasks/` deve retornar zero (após slice 2).
- [ ] `docker-compose.pipeline-service.yml` sobe pipeline-service em porta 8001.
- [ ] `GET /health` do backend inclui `pipeline_service_reachable: bool`.
- [ ] OpenAPI snapshot atualizado para backend + snapshot novo para pipeline-service.
- [ ] 0 regressão em `pytest tests -q` e `pytest backend/tests -q`.
- [ ] `dev/check_pipeline_boundaries.py` passa (pipeline-service importa pipeline/ de fora; pipeline/ intocado).
- [ ] ADR-112 escrita + CHANGELOG + BACKLOG atualizados.

---

## Rollback criteria — ABORTE se

- Qualquer teste golden (`test_e*_golden_execution.py`) passa a falhar.
- `pytest backend/tests -q` baseline cai >5 failures com `MATHOMS_PIPELINE_SERVICE_URL` desligada.
- `dev/check_pipeline_boundaries.py` falha (você importou `fastapi`/`sqlalchemy` dentro de `pipeline/`).
- Smoke (`make smoke-up`) não sobe pipeline-service em 60s.
- OpenAPI snapshot diverge de forma não-intencional (schemas alterados sem mudança de código real).

Em rollback: commitar tudo em branch, anunciar, abrir issue e voltar para `origin/main` limpo.

---

## Anti-patterns a evitar

- **Duplicar lógica de stages** em `pipeline-service/app/services/`. Pipeline-service **chama** `pipeline.orchestrator._run_stage`; não reescreve.
- **DB em pipeline-service.** Stateless rigoroso (ADR-111). Cache em Redis, state em chamadas HTTP.
- **Session longa de SQLAlchemy** cruzando HTTP boundary. Backend abre/fecha transação; pipeline-service nunca vê session.
- **Mudar contrato de `backend/app/schemas/pipeline.py`** por conveniência. Se precisar, ADR-109 exige snapshot sync — `make update-openapi-snapshot` + commit separado.
- **Cutover sem fallback.** `InProcessPipelineClient` tem que funcionar forever (dev, test, single-process deploy). Sem flag, sem cutover atômico.
- **Commits misturando slices.** Slice 1 = greenfield isolado. Slice 2 = backend adapter. Slice 3 = infra. Cada slice gate independente.

---

## Coordenação com outros agentes

Em paralelo a você, lanes ativas:

- `agent/a6g2-pipeline-style/*` — sweep `scripts/`, `pipeline/`, `tests/fixtures/`. **Zero overlap** com pipeline-service (greenfield).
- `agent/a6g4-frontend-style/*` — 🚧 2 worktrees ativos em `frontend/src/`. **Zero overlap**.
- `agent/a6g5-tests-sweep/*` — toca só `tests/**`, `backend/tests/**` (excluindo fixtures). **Overlap mínimo** em `backend/tests/test_pipeline_task.py` (A6g.5 renomeia testes; você altera imports nesse arquivo em slice 2). Resolver via rebase na ordem: A6g.5 merge primeiro, depois você rebase.
- `agent/a6e3-use-cases/*` — **scope limitado a FamilyMember + Category + Goal**, não toca `pipeline_task`/pipeline. Se agente A6e.3 tentar expandir para Document/Task/Config, você tem precedence (A6e.3 fica bloqueado até A6f.1 merge).

**Hotspots compartilhados:**

```bash
git fetch origin
git log -5 --oneline origin/main -- docs/CHANGELOG.md docs/BACKLOG.md docs/DECISIONS.md
```

Se agente mergeou hotspot <30min, espere 2min, anuncie, commite docs no **mesmo turno** (≤5min).

**Sync periódico (sessão >1h):** rode `git fetch origin && git log HEAD..origin/main` a cada 30min. Se `CLAUDE.md` mudou, releia §Code style e §Antes de pegar uma task.

---

## Referências

- [ADR-102](../DECISIONS.md) — language-neutral boundaries (R18-R20)
- [ADR-111](../DECISIONS.md) — stateless rigoroso
- [ADR-109](../DECISIONS.md) — auth portability + OpenAPI snapshot
- [ADR-110](../DECISIONS.md) — structured logs + OTel
- [CANONICAL_ENGINE_P0.md](../CANONICAL_ENGINE_P0.md) — fronteira pipeline atual
- [ARCHITECTURE.md §17](../ARCHITECTURE.md) — arquitetura alvo pós-A6
- [STATELESS_AUDIT.md](../STATELESS_AUDIT.md) — audit de estado mutável in-memory
- Prompts paralelos: [track_a6g2](track_a6g2_pipeline_style_sweep.md), [track_a6g4](track_a6g4_frontend_style_sweep.md), [track_a6g5](track_a6g5_tests_sweep.md), [track_a6e3](track_a6e3_use_cases.md)
