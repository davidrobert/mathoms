# Track A6e — Task aggregate slice (ADR-101, R12-R17)

> **Objetivo:** último slice de aggregate antes das transversais A6e.3/.4.
> Migra `backend/app/api/tasks.py` (482 linhas, 19 endpoints, 3 sub-agregados)
> para o padrão DDD/SOLID: repository + DTOs + router fino.
>
> **Por que esse slice é crítico:** Task é o único aggregate em `backend/app/api/`
> que ainda não foi migrado. Fechando ele, destrava-se **Onda 2** do plano de
> migração — A6e.3 (use cases) + A6e.4 (routers finos) são transversais e
> exigem que todos os agregados já estejam no padrão novo.

---

## Contexto de negócio

Task cobre **3 sub-agregados disjuntos** dentro do mesmo aggregate root:

1. **Tarefas financeiras** — core (prazo, status, linked_goal_id, progress)
2. **Sugestões de tarefas** (`TaskSuggestion`) — geradas por LLM/pipeline; fluxo approve/reject/merge
3. **Anexos** (`TaskAttachment`) — arquivos em disco via `StorageService`

Todos os 3 compartilham `workspace_id` e estão em `backend/app/models/task.py`
(308 linhas, 3 classes: `Task`, `TaskSuggestion`, `TaskAttachment`).

**Fonte adicional:** `tasks.py` tem endpoint `GET /tasks/export.md` (markdown),
e outros serviços (`task_notification_service`, `report_tasks_snapshot_service`,
`task_suggestion_service`) fazem queries diretas ao ORM — **ficam fora do
escopo** deste slice (R15 use-case layer, próximo slice).

---

## Estado atual (baseline)

```
backend/app/api/tasks.py              482 linhas, 19 endpoints
backend/app/schemas/task.py           231 linhas (Pydantic legado)
backend/app/models/task.py            308 linhas (3 classes ORM)
backend/app/services/task_service.py              ~7 funções async
backend/app/services/task_suggestion_service.py   ~7 funções async
backend/app/services/task_attachment_service.py   ~5 funções async
```

**19 endpoints em `tasks.py`:**
```
GET    /tasks                              — lista com filtros
GET    /tasks/upcoming                     — próximas N
GET    /tasks/export.md                    — markdown export (PlainTextResponse)
POST   /tasks/scan-deadlines               — varredura de prazos
GET    /tasks/{task_id}
GET    /tasks/{task_id}/progress
POST   /tasks/{task_id}/... (várias ações — transitions, attachments, etc)
PATCH  /tasks/{task_id}
GET    /tasks/{task_id}/attachments
POST   /tasks/{task_id}/attachments
DELETE /tasks/{task_id}
DELETE /tasks/{task_id}/attachments/{att_id}
...
(Use grep "^@router" backend/app/api/tasks.py para a lista exata de 19.)
```

**Services já extraídos** (`task_service.py`, `task_suggestion_service.py`,
`task_attachment_service.py`) — **NÃO reescrever**. Eles fazem business logic
correta; o slice só insere a camada **repository + DTO** entre router e service,
e elimina queries diretas `select(Task)` no router.

**Query audit (pontos de ORM direto no router):**

```bash
grep -n "db.execute\|db.get\|select(" backend/app/api/tasks.py
# (esse é o inventário a reduzir a zero via repo.X calls)
```

---

## Blueprint — use o slice Goal como template exato

O slice A6e Goal foi mergeado 2026-04-21 e é o template mais próximo (também
tem sub-agregados: `IFGoal`, `AporteGoal`, `AlocacaoGoal`, `DolarGoal`).
Reproduza a mesma estrutura:

### Commits do Goal slice (leia em ordem)

```
a789700  backend(repos): GoalRepository async (A6e.6 — ADR-101)
6bc4754  backend(dto): goal response/command/compute/mapper — 4 tipos (A6e.6 — ADR-101)
db34363  backend(api): goals.py usa GoalRepository + DTOs (A6e.6)
ad6ae5f  test(backend): Goal DTO mapper + repository (A6e.6 — 28 testes)
632edf7  docs(api): openapi snapshot — A6e.6
888ce45  docs(a6e.6): CHANGELOG + BACKLOG marcam slice Goal ✅
```

**Estrutura alvo:**

```
backend/app/repositories/task_repository.py         (NOVO)
backend/app/schemas/dto/task/
├── __init__.py
├── base.py           (shared validators/constants)
├── command.py        (TaskCreateCommand, TaskUpdateCommand, ...)
├── response.py       (TaskResponse, TaskListResponse, TaskProgressResponse,
│                      SuggestionResponse, AttachmentResponse, ...)
├── suggestion.py     (sub-aggregate DTOs)
├── attachment.py     (sub-aggregate DTOs)
└── mapper.py         (puro, testável sem DB)
backend/app/schemas/task.py         (vira shim re-exportando nomes legados)
backend/app/api/tasks.py            (≤250 linhas pós-slice; grep select\(Task = 0)
backend/tests/test_task_dto_mapper.py        (NOVO — puros)
backend/tests/test_task_repository.py        (NOVO — DB real)
```

### Outros slices como referência secundária

| Slice        | Repo + DTO commits                                                             | Uso                                   |
| ------------ | ------------------------------------------------------------------------------ | ------------------------------------- |
| Document     | `df52d07`/`e281d9f`/`3c00835`/`02d0d74`/`e15efde`/`66016b2`                    | Savepoint pattern (upload), fuzzy dedupe |
| ConfigBlob   | `1d7562f` (merge)                                                              | Deep-merge helper puro                |
| Category     | parte de `ab240aa` anterior                                                     | CRUD simples                          |
| FamilyMember | `c84af46`/`2d9074b`/`13ece89`/`4167fa5`                                         | Vault Protocol, sub-entidade BankAccount |

Task tem overlap com Goal (sub-agregados dentro do mesmo aggregate) e com
Document (arquivos em disco via StorageService). Combine os dois patterns.

---

## Regras do slice (invariantes — enforced por tests)

Tiradas do CLAUDE.md e ADR-101 (R12-R17):

### R12 — DTO ↔ Model

- **Zero `Model.from_orm()`** em endpoints. Mapper puro em `mapper.py`.
- **Command DTOs** (`TaskCreateCommand`, `TaskUpdateCommand`) com validators
  Pydantic v2; **response DTOs** (`TaskResponse`, etc) imutáveis.
- Mapper recebe apenas o ORM + eventuais dependências via Protocol
  (ex.: `StorageService` para Attachment se mapper precisar resolver paths).

### R13 — workspace_id no predicado

- **TODO** método do repo recebe `workspace_id` e inclui em `.where(...)`.
- Zero chance de cross-tenant leak. `test_task_repository.py` deve ter um
  assert por método que valida isolation multi-tenant.

### R14 — Repo não commita

- Caller é dono do boundary transacional. Upload de anexo (parecido com
  Document) pode usar savepoint — estudar `api/documents.py` flow.

### R15 — Services ficam como estão

- Não reescrever `task_service.py`, `task_suggestion_service.py`,
  `task_attachment_service.py`. Eles podem continuar usando `db.execute(...)`
  internamente — **migração deles é R15 (use-case layer)**, slice futuro.
- O router chama: `repo.X(...)` para queries simples; `service.Y(db, ...)`
  para operações complexas que já moram nos services.

### R17 — Compat binária

- `backend/app/schemas/task.py` vira **shim** — re-exporta todos os nomes
  legados (`TaskCreate`, `TaskUpdate`, `TaskResponse` legado, etc). Aliases
  onde necessário (`TaskCreate = TaskCreateCommand`).
- Teste existente `backend/tests/test_tasks*.py` (se houver) passa sem
  modificação.

---

## Sequência de execução (branch + commits atômicos)

### 1. Setup (5 min)

```bash
git fetch origin
git checkout -b agent/a6e-task/$(date +%Y%m%d-%H%M)
git log --oneline origin/main -5   # confirma estado
```

### 2. Baseline antes de editar

```bash
cd backend && pytest tests -q --tb=no -x 2>&1 | tail -20
# Anotar: quantos passed, quantos failed. Tudo que falhar agora deve
# continuar falhando ao fim (não introduzir regressão).
```

### 3. Commits ordenados (5 commits canônicos + openapi + docs)

**Commit 1** — `backend(repos): TaskRepository async (A6e.task — ADR-101)`
- Cria `backend/app/repositories/task_repository.py`
- Métodos inferidos dos `db.execute(select(Task))` do router — um por query
  distinta. Nomes: `list(workspace_id, filters)`, `get_by_id(id, workspace_id)`,
  `list_upcoming(...)`, `get_with_suggestions(...)`, `list_attachments(...)`,
  `add(task)`, `delete(task_id, workspace_id)`, etc.
- **Todos async**, **todos com `workspace_id` no predicado**, **nenhum commita**.
- **Zero side-effects de import** (sem `init_*` em top-level).

**Commit 2** — `backend(dto): task response/command/mapper — 3 sub-agregados (A6e.task — ADR-101)`
- `schemas/dto/task/` com subpastas para os 3 sub-agregados.
- `mapper.py` puro (não importa DB). Recebe `StorageService` via Protocol
  se precisar mapear attachment paths.
- `base.py` com validators compartilhados (ex.: priority enum, status enum).
- Commands com `model_validator` v2 equivalentes aos validators do
  `schemas/task.py` legado.

**Commit 3** — `backend(api): tasks.py usa TaskRepository + DTOs (A6e.task)`
- Refactor `backend/app/api/tasks.py`:
  - `Depends(_get_task_repo)` em cada endpoint
  - `grep "select(Task\|select(TaskSuggestion\|select(TaskAttachment" backend/app/api/tasks.py` = vazio
  - Endpoints retornam DTOs, nunca ORM
  - Services (`task_service.X`, `task_suggestion_service.Y`) continuam
    sendo chamados onde faz sentido (não duplicar lógica no router)
- `schemas/task.py` vira shim (re-exporta nomes legados)
- **Preserve comentários inline existentes** (CLAUDE.md regra)
- Meta de tamanho: `tasks.py` **≤250 linhas** pós-refactor (era 482)

**Commit 4** — `test(backend): Task DTO mapper + repository (A6e.task — N testes)`
- `backend/tests/test_task_dto_mapper.py` — puros, sem DB. Cobrir:
  - `task_to_response` com/sem linked_goal, com/sem attachments
  - `suggestion_to_response` approved vs pending vs rejected
  - `attachment_to_response` com path resolution via Protocol fake
  - Empty-string → None validators em Commands (paridade com legado)
- `backend/tests/test_task_repository.py` — DB real. Cobrir:
  - `workspace_id` isolation em **todos** os métodos (test com 2 workspaces)
  - `list` com filtros (status=done, priority, prazo ranges) — respeita combos
  - `get_by_id` retorna None em cross-tenant (não `404`, o router cuida disso)
  - Ordenação deterministic (`created_at DESC` ou o que o legado faz)
  - `delete` em cascade de attachments/suggestions quando aplicável
- Meta: ~30 testes novos, zero regressão nos existentes.

**Commit 5** — `docs(api): openapi snapshot — A6e.task`
```bash
make update-openapi-snapshot
git add docs/api/v1/openapi.json
```
Confirma que renames de DTOs (ex.: `TaskCreate` → `TaskCreateCommand`) aparecem
e que o teste `backend/tests/test_openapi_snapshot.py` está verde.

**Commit 6** — `docs(a6e.task): CHANGELOG + BACKLOG marcam slice Task ✅`
Edita em **commit separado** (regra hotspot):
- `docs/CHANGELOG.md` → nova entrada em `[Unreleased]` seguindo exato formato
  das entradas Goal/Document.
- `docs/BACKLOG.md` → §A6e:
  - Linhas A6e.1/.2: adicionar `+ task` nos agregados entregues
  - Adicionar bloco `#### Slice entregue — **Task aggregate**` após o
    bloco de Goal, seguindo o mesmo template
  - Header §Sprint A6: atualizar "5 agregados" → "6 agregados"; remover
    "Próximo: Task" do bullet A6e
  - Bloco "Próximas etapas — ondas paralelas":
    - Remover Lane A1 (A6e Task) da Onda 1
    - Se sobrar só A6g.2 e A6g.4, promover A6g.5 (tests sweep) da Onda 2
      para Onda 1 — baseline A6g.1 já permite
    - Atualizar seta "após A6e Task merged — Goal já ✅" para
      "Onda 1 = só A6g sweeps; transversais A6e.3/.4 destravadas"

### 4. Gates de push

```bash
# Na ordem:
.venv/bin/pre-commit run --all-files
cd backend && pytest tests -q             # zero regressão vs baseline
cd .. && pytest tests -q                   # pipeline não afetado
# Se tocou frontend (não deveria): cd frontend && npm test -- --run

git fetch origin
BEHIND=$(git rev-list --count HEAD..origin/main)
[ "$BEHIND" -gt 0 ] && git rebase origin/main && cd backend && pytest tests -q

git push origin HEAD:main   # fast-forward only
```

### 5. Sync local main pós-merge

```bash
git checkout main && git pull --ff-only origin main
git log --oneline -5   # confirma commits em origin/main
```

---

## Critérios de aceite (binários)

- [ ] `backend/app/repositories/task_repository.py` existe; todos os métodos async; workspace_id em todas as queries
- [ ] `backend/app/schemas/dto/task/{response,command,mapper,base}.py` existe; mapper não importa DB
- [ ] `grep -c "select(Task" backend/app/api/tasks.py` = 0
- [ ] `grep -c "select(TaskSuggestion" backend/app/api/tasks.py` = 0
- [ ] `grep -c "select(TaskAttachment" backend/app/api/tasks.py` = 0
- [ ] `wc -l backend/app/api/tasks.py` mostra ≤250 linhas
- [ ] `backend/app/schemas/task.py` existe como shim compat — imports antigos continuam funcionando
- [ ] `pytest backend/tests -q` tem **pelo menos +25 tests novos** (mapper + repo)
- [ ] `pytest backend/tests -q` zero regressões vs baseline pré-slice
- [ ] `make update-openapi-snapshot` commitado; `test_openapi_snapshot.py` verde
- [ ] 6 commits em `origin/main` fast-forward (repo · dto · router · tests · openapi · docs)
- [ ] `docs/BACKLOG.md` §A6e reflete o slice (linha agregados + bloco "Slice entregue" + header + Ondas)
- [ ] `docs/CHANGELOG.md [Unreleased]` tem entrada estruturada

---

## Fora de escopo (deixar documentado em "Escopo deixado para frente")

- **R15 use-case layer:** `task_service.py`, `task_suggestion_service.py`,
  `task_attachment_service.py` continuam com ORM direto — serão migrados
  no slice A6e.3 (application layer).
- **`task_notification_service.py`, `report_tasks_snapshot_service.py`,
  `pipeline_adapter.py`:** outros consumidores de Task ORM fora do router.
  Mesma razão, mesmo slice futuro.
- **Refactor tamanho de funções em `tasks.py`:** fica para A6g.3 (backend
  code style sweep), após A6e.4 (routers finos transversais).

---

## Coordenação com outros agentes (protocolo)

Em paralelo a você podem estar rodando (Onda 1):
- `agent/a6g2-pipeline-style/*` — refactor em `pipeline/` + `scripts/`. **Zero
  overlap** com backend/app/.
- `agent/a6g4-frontend-style/*` — refactor em `frontend/src/`. **Zero overlap**.

**Hotspots que você VAI editar** (anunciar + commit atômico ≤5 min):
- `docs/CHANGELOG.md` (commit 6)
- `docs/BACKLOG.md` (commit 6)

Antes de cada commit hotspot:
```bash
git fetch origin
git log -5 --oneline origin/main -- docs/CHANGELOG.md docs/BACKLOG.md
```
Se log mostra commit <30min do outro agente em um desses arquivos, **pause 2
min, anuncie, commite atômico**.

Sync periódico a cada ~30min em sessão longa:
```bash
git fetch origin && git log --oneline HEAD..origin/main
```
Se mover ≥1 commit, rebase incremental antes de continuar.

---

## Rollback criteria

Aborte o slice e reabra discussão se:
- `task_service.py` precisar ser reescrito para o repo funcionar (sinaliza
  que a fronteira repo/service não está clara — revisar ADR-101 R15)
- Mais de 3 testes legados de `test_tasks*.py` (ou similar) falharem pós-shim
  (sinaliza compat quebrada — fix antes de seguir)
- `tasks.py` pós-refactor ficar **maior** que 250 linhas (sinaliza que lógica
  não moveu para service; não apenas "escondeu" em DTOs)

---

## Entregáveis finais para o próximo agente ler

Após merge, o próximo agente (quem pegar Onda 2) deve conseguir:

1. Ler `docs/BACKLOG.md` §A6e e ver **6 agregados** entregues, Task listado.
2. Executar `grep -rn "select(Task" backend/app/api/` e obter zero resultados.
3. Usar `backend/app/repositories/task_repository.py` como template para
   eventual slice A6e.3 (use cases) pegando Task.
4. Ver em `docs/CHANGELOG.md [Unreleased]` a entrada Task seguindo o mesmo
   formato estrutural das entradas Goal/Document.

Onda 2 destravada: A6e.3 (use cases) + A6e.4 (routers finos) agora podem
processar todos os 6 agregados uniformemente.
