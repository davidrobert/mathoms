# Track A6e.3b — Application layer: ConfigBlob + Document + Task (use cases)

> **Lane ID:** A6e.3b
> **Branch prefix:** `agent/a6e3b-use-cases-rest/*`
> **Depende de:** A6e.3 ✅ (padrão estabelecido em FamilyMember/Category/Goal) + A6f.1 ✅ (`HttpPipelineClient` permite desacoplar Document/Task do pipeline Celery direto).
> **Paralelo com:** A6e.4 (4a, não-pipeline-adjacentes), A6e.5 (/v1 prefix), A6e.6 (events), A6g.2, A6g.4, A6g.7 — **zero overlap se respeitar escopo abaixo**.
> **Conflita com:** commits em `backend/app/api/config.py`, `backend/app/api/documents.py`, `backend/app/api/tasks.py`, `backend/app/services/document_processor.py`, `backend/app/services/task_service.py`, `backend/app/services/config_defaults.py`. A6e.4 4b é **continuação** desta lane — **não começar 4b antes desta mergear**.
> **Onda:** 2
> **Índice de prompts:** [README.md](README.md)
> **Fonte de verdade:** [ADR-101 R15 application layer](../DECISIONS.md), [ADR-112 pipeline-as-service](../DECISIONS.md), [CLAUDE.md §Code style](../../CLAUDE.md#code-style), [BACKLOG §A6e](../BACKLOG.md), [track_a6e3](track_a6e3_use_cases.md) (padrão de referência)

> **Objetivo:** completar a application layer (ADR-101 R15) para os 3
> aggregates que ficaram de fora de A6e.3 — ConfigBlob, Document, Task
> — seguindo o mesmo padrão (1 endpoint = 1 use case em
> `backend/app/application/<aggregate>/<verb>_<noun>.py`, testável via
> `FakeRepository`). Desbloqueia **A6e.4 fase 4b** (thin routers para
> `documents.py`, `tasks.py`, `config.py`).

---

## Por que esta lane agora

- **A6e.3 ✅** entregou o padrão (22 use cases, 56 testes puros) em 3 aggregates. Os outros 3 ficaram deferred por dependerem de pipeline/Celery direto.
- **A6f.1 ✅** (ADR-112) extraiu o pipeline em serviço HTTP standalone. Document e Task não precisam mais importar `pipeline_task` diretamente — podem chamar `HttpPipelineClient` em use cases. A dependência que bloqueava caiu.
- **A6e.4 4b** (thin routers para `documents.py` 769, `tasks.py` 487, `config.py` 464 → ≤100 cada) precisa de use cases prontos. Esta é o pré-requisito.
- **Desbloqueia A6g.3** (backend sweep) + **A6g.6** (enforcement) ao completar a superfície DDD.

---

## Regras inegociáveis

Mesmas de [track_a6e3](track_a6e3_use_cases.md#regras-inegociáveis). Resumo:

1. **1 endpoint = 1 use case** em `application/<agg>/<verb>_<noun>.py`.
2. **Use case não conhece FastAPI.** Recebe DTOs + Protocols, retorna DTOs. Erros = exceções de domínio tipadas.
3. **Repos via Protocol** (duck-typed; fakes injetados em testes).
4. **Serviços computacionais puros permanecem** — use case **chama**, não recalcula.
5. **Funções 4-20 linhas, arquivos ≤500, nomes específicos** (§Code style).
6. **Dinheiro nunca é `float`** (ADR-090).
7. **Type hints obrigatórios**.
8. **Response models preservados** (ADR-109); mudança de shape = fora do escopo.
9. **Preserve comentários existentes em refactor**.
10. **`HttpPipelineClient` (A6f.1) é o boundary** para chamadas de pipeline — nenhum use case importa `pipeline_task` ou `celery` direto.

---

## Estado atual — universo mapeado

**Aggregates deste slice** (já têm repo+DTO em A6e per-aggregate, faltam use cases):

| Aggregate | Router hoje | Service atual | Complexidade | Use cases esperados |
|---|---|---|---|---|
| **ConfigBlob** | `config.py` parte (~300 linhas após A6e.3 remover FamilyMember/Category) | `config_service.py` + `institutions_service.py` + `llm_config_service.py` | Média — múltiplos sub-schemas (institutions, llm_providers, reconciliation, categorization) | 6-8 (get/update por sub-schema + reset + validate) |
| **Document** | `documents.py` 769 | `document_processor.py` + `document_classification.py` + `content_classifier.py` | Alta — upload, classificação (regex + LLM), dedupe, preview, delete, reclassify | 8-10 (upload, classify, reclassify, list, get_preview, delete, get_content_hash, list_duplicates) |
| **Task** | `tasks.py` 487 | `task_service.py` + sub-agregados (Budget, Goal linkage) | Alta — CRUD + assignment + sub-aggregate Budget + Goal linkage | 10-12 (create/update/complete/delete task + budget CRUD + goal linkage) |

**Sub-agregados de Task (entregues em A6e.7 com DTOs prontos):**
- `TaskBudget` — orçamento associado
- `TaskGoalLink` — vínculo com Goal
- `TaskAssignee` — membro atribuído

**Arquivos off-limits neste slice:**

```
backend/app/api/family_members.py       # A6e.3 já fez
backend/app/api/categories.py           # A6e.3 já fez
backend/app/api/goals.py                # A6e.3 + será finada em A6e.4 4a
backend/app/api/pipeline.py             # A6e.4 4a (HttpPipelineClient)
backend/app/application/family_member/  # A6e.3
backend/app/application/category/       # A6e.3
backend/app/application/goal/           # A6e.3
```

---

## Alvo estrutural

```
backend/app/application/
  config_blob/
    __init__.py
    _protocols.py                       # ConfigBlobRepository Protocol
    get_institution_config.py
    update_institution_config.py
    get_llm_provider_config.py
    update_llm_provider_config.py
    get_reconciliation_config.py
    update_reconciliation_config.py
    get_categorization_rules.py
    update_categorization_rules.py
    reset_config_to_defaults.py
    validate_config_schema.py
  document/
    __init__.py
    _protocols.py                       # DocumentRepository, ClassificationService, PipelineClient Protocols
    _helpers.py                         # helpers internos (hash, content extract)
    upload_document.py
    classify_document.py                # wrap de classify_document existente em document_classification.py
    reclassify_document.py
    list_workspace_documents.py
    get_document_preview.py
    delete_document.py
    list_duplicate_candidates.py
    update_document_metadata.py
  task/
    __init__.py
    _protocols.py                       # TaskRepository, TaskBudgetRepository, TaskGoalLinkRepository Protocols
    create_task.py
    list_workspace_tasks.py
    update_task.py
    complete_task.py
    delete_task.py
    assign_task.py
    create_task_budget.py
    update_task_budget.py
    delete_task_budget.py
    link_task_to_goal.py
    unlink_task_from_goal.py
    list_task_goal_links.py
```

**Total estimado:** 28-30 use cases (vs 22 em A6e.3).

---

## Sequência de slices

### Slice 1 — ConfigBlob (1 sessão)

**Por que primeiro:** menor complexidade, zero dependência de pipeline/LLM/async side-effects. Mostra que o padrão escala para aggregate com sub-schemas.

**Passos:**

1. Criar `backend/app/application/config_blob/_protocols.py`:
   ```python
   class ConfigBlobRepository(Protocol):
       async def get(self, workspace_id: str, config_key: str) -> ConfigBlob | None: ...
       async def upsert(self, blob: ConfigBlob) -> ConfigBlob: ...
       async def delete(self, workspace_id: str, config_key: str) -> None: ...
   ```
2. Criar 10 use cases (1 arquivo cada, 8-25 linhas).
3. `validate_config_schema` consome `ConfigSchemaValidator` (domain puro, já em `backend/app/domain/` ou `config_defaults.py`).
4. Testes em `backend/tests/application/config_blob/` com `FakeConfigBlobRepository` em `backend/tests/fakes/config_blob.py`. 1 arquivo de teste por use case. Sem DB.
5. **Não** reescrever `config.py` (router) ainda — isso é A6e.4 4b.

**Gate:**
- `pytest backend/tests/application/config_blob/ -q` verde, **sem DB**, <3s.
- Zero regressão em `pytest backend/tests/ -q`.
- `grep -rn "from backend.app.services.config_service\|institutions_service\|llm_config_service" backend/app/application/` aceitável (use cases podem chamar services computacionais durante transição); não deve aparecer em routers novos.

**Commit 1:** `refactor(backend): extract ConfigBlob use cases (A6e.3b slice 1)`

### Slice 2 — Task (1 sessão grande, sub-aggregates)

**Por que segundo:** Task tem sub-agregados (Budget, GoalLink, Assignee) — mostrar que o padrão lida com isso. Document tem classificação LLM + pipeline client; deixar para último.

**Considerações especiais:**
- `link_task_to_goal` — cross-aggregate (Task → Goal). Use case **não** consulta Goal repo direto; recebe `goal_id` e valida existência via `GoalRepository` injetado como Protocol. Evita circular dependency.
- `complete_task` emite evento — para esta lane, apenas chame `repo.mark_complete(...)`; A6e.6 adicionará `emit_event()` depois.
- `TaskBudget` CRUD é CRUD puro; se cada use case for <10 linhas, considere agrupar em `manage_task_budget.py` com funções nomeadas (`create_budget`, `update_budget`, `delete_budget`) — **exceção justificada** ao padrão 1-use-case-por-arquivo. Documente no docstring.

**Passos:** igual A6e.3 pattern. 10-12 use cases, testes puros em `backend/tests/application/task/` com `FakeTaskRepository`, `FakeTaskBudgetRepository`, `FakeTaskGoalLinkRepository`, `FakeGoalRepository` (para validação cross-aggregate).

**Gate:**
- Testes <5s.
- Goldens de task_service (se existem) continuam verdes.
- Cross-aggregate validado: `FakeGoalRepository` retornando `None` → use case levanta `GoalNotFoundError` apropriado.

**Commit 2:** `refactor(backend): extract Task + sub-aggregates use cases (A6e.3b slice 2)`

### Slice 3 — Document (1 sessão grande, pipeline + LLM)

**Por que por último:** maior complexidade. Upload envolve: (a) hash + dedupe, (b) extração de conteúdo, (c) classificação (regex + LLM fallback), (d) trigger de pipeline via `HttpPipelineClient` (A6f.1).

**Considerações especiais:**
- `upload_document` recebe bytes + filename + workspace; retorna `DocumentUploadResponse`. Internamente orquestra: hash → dedup check → extract content → classify → save → `pipeline_client.start_run(document_id)`.
- `ClassificationService` Protocol wraps `document_classification.classify_document` (ADR-081). Use case injeta; teste passa fake que retorna classificação fixa.
- `PipelineClient` Protocol é implementado por `HttpPipelineClient` (A6f.1). Fake em teste retorna `PipelineRunStarted(run_id=...)` sem side-effect.
- `reclassify_document` chama `classify_document` com modo force=True; não dispara pipeline novamente.
- `list_duplicate_candidates` consulta `possible_duplicate_of_id` de dedupe fuzzy (regra já em DB, partial unique index).
- **Não** mover `document_classification.py` para `application/` — é service de domínio com regras regex + LLM; use case chama.

**Passos:** padrão + 4 Protocols (Repository, ClassificationService, PipelineClient, ContentExtractor). Fakes em `backend/tests/fakes/document.py`.

**Gate:**
- `pytest backend/tests/application/document/ -q` <8s, **sem DB, sem LLM real**.
- `upload_document` teste: fake classification retorna `("faturaunique", 0.95)` → use case grava + chama `pipeline_client.start_run()` → assertion no fake.
- Integração (uma vez, opcional neste slice) com MSW/TestClient real verifica que o novo use case produz response idêntico ao router legado.

**Commit 3:** `refactor(backend): extract Document use cases (A6e.3b slice 3)`

### Commit N+1 — docs (hotspot, ≤5min)

- `docs/CHANGELOG.md [Unreleased]`: A6e.3b — 28+ use cases, 70+ tests, 6 aggregates no total na application layer.
- `docs/BACKLOG.md`: A6e.3b ☐ → ✅; atualizar "Restante" no topo do Sprint A6 (remover A6e.3b, promover A6e.4 para pickable sem restrição).
- `docs/ARCHITECTURE.md §17` se menciona estado da application layer — sincronizar.
- Considerar ADR-113 (ou próximo livre) se emergir padrão novo (ex.: sub-aggregate como função-grupo; cross-aggregate validation via Protocol) — opcional.

**Commit 4:** `docs(a6e.3b): CHANGELOG + BACKLOG — application layer completa`

---

## Critérios de aceite (binários)

- [ ] `backend/app/application/{config_blob,document,task}/` existem com 28-30 use cases no total (1 por arquivo, exceto sub-aggregate agrupado documentado).
- [ ] `backend/tests/application/{config_blob,document,task}/` existem com testes puros sem DB.
- [ ] `backend/tests/fakes/{config_blob,document,task}.py` com fakes nomeados (não `MagicMock`).
- [ ] Cada Protocol (`_protocols.py`) lista ≥1 método por use case consumidor.
- [ ] Cross-aggregate validado: fakes de GoalRepository (em Task use cases) e ClassificationService/PipelineClient (em Document) injetáveis.
- [ ] `pytest backend/tests/application/ -q` verde em <15s (6 aggregates agora).
- [ ] `pytest backend/tests/ -q` zero regressão; ≥990 testes.
- [ ] `grep -rn "from fastapi\|HTTPException\|Depends" backend/app/application/` = 0.
- [ ] `grep -rn "pipeline_task\|celery" backend/app/application/document/` = 0 (boundary A6f.1).
- [ ] OpenAPI snapshot intocado (esta lane **não** mexe em routers).
- [ ] `pre-commit run --all-files` passa.

---

## Rollback criteria — ABORTE se

- `document_classification.classify_document` tem side effect oculto (mutação de estado global) que quebra quando chamado de use case — é bug preexistente; reporte em issue e adie.
- `task_service` depende de estado em memória que quebra em use case stateless (ADR-111) — refactor de estado é fora do escopo; adie slice Task.
- `HttpPipelineClient` não expõe o método que o use case precisa (ex.: `cancel_run` se essencial) — abra issue em A6f.1b; use case fica `NotImplementedError` no slice e volta depois.
- `config.py` tem endpoint que agrega dados cross-aggregate (ex.: `GET /config/dashboard-overview`) que não cabe em 1 use case — classifique como "composite read" e adie para A6e.4 (o router mantém composição explícita).

Em rollback: `git reset --hard origin/main` na branch local, anuncia, abre issue com o slice específico.

---

## Anti-patterns a evitar

- **Use case que recebe `AsyncSession`.** Sessão é responsabilidade do repo + outer. Use case recebe Protocol; repo injetado implementa com sessão.
- **Use case que inicia `AsyncTask` / `BackgroundTasks` / `create_task`.** Viola ADR-111 (stateless). Side-effect assíncrono vai para Celery via `HttpPipelineClient` ou para domain event (A6e.6).
- **Reusar `*Request` Pydantic como Command.** Crie `*Command` explícito — marca a fronteira HTTP→application.
- **Service computacional virando use case.** `document_classification.classify_document` continua service; `classify_document_use_case` **chama** o service.
- **Chamar `pipeline_task.run_pipeline.delay(...)` direto.** Viola A6f.1. Use `HttpPipelineClient` injetado como Protocol.
- **Misturar slices em 1 commit.** Cada aggregate = 1 commit (+ 1 de testes se extenso). Rebase com 3 aggregates num commit = impossível.
- **Circular import via cross-aggregate.** Task use case não importa `Goal` model; usa `GoalRepository` Protocol. Implementação do repo fica em `repositories/` (resolve circular em runtime).
- **"Validar shape" no use case com Pydantic duplicado.** Command já é Pydantic; validação de shape é do FastAPI boundary. Use case valida **regras de negócio** (conflito, ownership, transição de estado).

---

## Coordenação com outros agentes

Lanes ativas ou prováveis (confirme com `git worktree list` + `git for-each-ref`):

- `agent/a6e4-thin-routers/*` — **esta lane é pré-requisito para A6e.4 fase 4b**. A6e.4 4a (14 routers não-pipeline) pode rodar em paralelo sem overlap. Se A6e.4 iniciou 4a antes de você, zero conflito; se 4b começou prematuramente, pare e coordene.
- `agent/a6e5-v1-prefix/*` — `main.py` + `core/config.py` + `lib/api/core.ts`. Zero overlap com `application/` e `tests/application/`.
- `agent/a6e6-domain-events/*` — events emitidos de use cases. **Overlap real** em `backend/app/application/task/complete_task.py` (emitirá `TaskCompletedEvent`) e `document/upload_document.py` (emitirá `DocumentUploadedEvent`). Resolva: você **não** emite eventos neste slice; A6e.6 adiciona depois num commit pequeno por use case.
- `agent/a6g2-pipeline-style/*` — `scripts/`, `pipeline/`. Zero overlap. (Mas `pipeline-service/` de A6f.1 pode continuar evoluindo — checar `git log -5 -- pipeline-service/` antes de mockar `HttpPipelineClient`.)
- `agent/a6g3-backend-style/*` — `backend/app/services/`, `backend/app/repositories/`. Você **não** deve renomear services; só chamá-los via Protocol de use case. A6g.3 renomeia services quando pegar; seu use case importa pelo nome atual, rebase resolve.
- `agent/a6g7-go-prep/*` — Go infra. Zero overlap.

**Hotspots compartilhados:**

```bash
git fetch origin
git log -5 --oneline origin/main -- \
  backend/app/application/ \
  backend/tests/application/ \
  backend/tests/fakes/ \
  docs/CHANGELOG.md docs/BACKLOG.md
```

**Regras de cadência:**
- Commite cada slice (1 aggregate) imediatamente após testes verdes. Não acumule 3 aggregates num commit.
- Sessão pausando mid-slice → `chore(wip): ponto de parada A6e.3b slice N` antes de sair.
- Docs (`CHANGELOG`, `BACKLOG`) commitam **por último**, depois do push dos 3 slices.

**Sync periódico (sessão >2h):**

```bash
git fetch origin && git log --oneline HEAD..origin/main
# Se application/goal ou application/family_member mudaram, releia
# padrão (A6e.6 pode ter adicionado emissão de eventos).
```

---

## O que esta lane NÃO entrega (explicitar no CHANGELOG)

- **Thin routers para `documents.py`, `tasks.py`, `config.py`** — A6e.4 fase 4b, lane subsequente.
- **Emissão de domain events** (`TaskCompletedEvent`, `DocumentUploadedEvent`) — A6e.6.
- **Refactor de `document_classification.py` / `task_service.py`** — A6g.3 backend sweep.
- **Migração /api/v1/** — A6e.5.
- **Enforcement AST** (teste de thin router) — A6e.4.
- **Substituir MagicMock remanescente em tests antigos** — A6g.5 já fechou Tiers 1-4; caso apareça hit novo, fora do escopo (novo teste já nasce com fake nomeado).

---

## Referências

- [ADR-101](../DECISIONS.md) — R15 application layer + R16 thin routers
- [ADR-112](../DECISIONS.md) — pipeline-as-service (fornece `HttpPipelineClient`)
- [ADR-081](../DECISIONS.md) — classificação unificada de documentos
- [track_a6e3_use_cases.md](track_a6e3_use_cases.md) — padrão de referência (FamilyMember/Category/Goal)
- [track_a6e4_thin_routers.md](track_a6e4_thin_routers.md) — próxima lane (consome seus use cases)
- [track_a6f1_pipeline_service.md](track_a6f1_pipeline_service.md) — contrato de `HttpPipelineClient`
- Slice modelo de use case: [backend/app/application/goal/create_if_goal_version.py](../../backend/app/application/goal/create_if_goal_version.py)
- BACKLOG §A6e — status e lanes ativas
