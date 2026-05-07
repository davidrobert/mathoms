---
id: TRACK-a6e3-use-cases
type: track
title: "Track A6e.3 — Application Layer (use cases) — slice inicial"
sprint: A6
status: consumed
created_at: null
consumed_at: null
agent_role: null
tags:
  - type/track
  - sprint/a6
  - status/consumed
---

# Track A6e.3 — Application Layer (use cases) — slice inicial

> **Lane ID:** A6e.3
> **Branch prefix:** `agent/a6e3-use-cases/*`
> **Depende de:** A6e per-aggregate ✅ (FamilyMember, Category, Goal repos+DTOs prontos)
> **Paralelo com:** A6f.1 pipeline-service, A6g.2 pipeline sweep, A6g.5 tests sweep — zero overlap **se** o slice respeitar os agregados abaixo.
> **Conflita com:** qualquer commit em `backend/app/api/pipeline.py`, `backend/app/services/pipeline_service.py`, `backend/app/tasks/pipeline_task.py` (A6f.1 tem precedence); qualquer commit em `backend/app/api/config.py`, `backend/app/api/documents.py`, `backend/app/api/tasks.py` (agregados pipeline-adjacentes).
> **Onda:** 2
> **Índice de prompts:** [README.md](README.md)
> **Fonte de verdade:** [CLAUDE.md §Code style](../../CLAUDE.md#code-style), [ADR-101](../DECISIONS.md), [BACKLOG §A6e](../BACKLOG.md)

> **Objetivo:** extrair a **application layer** do backend — cada endpoint
> delega a 1 use case em `backend/app/application/<aggregate>/<verb>_<noun>.py`,
> testável sem DB via fakes. Este slice cobre **3 agregados seguros**
> (FamilyMember, Category, Goal) — explicitamente **fora** de
> Document/Task/Config/Pipeline para evitar merge hell com A6f.1.

---

## Por que este slice agora

A6e per-aggregate concluiu 6 agregados com repo+DTO. Próximo passo
(ADR-101 R15) é "1 endpoint = 1 use case" — routers ficam finos
delegando para application layer; use cases são testáveis sem DB usando
`FakeRepository`. Isso:
- Destrava A6e.4 (routers ≤50 linhas) — sem use case, router não tem para onde encolher.
- Destrava A6e.events (domain events, ex-`A6e.6`) — use case é o ponto natural para emitir eventos.
- Destrava testes unitários puros de regras de negócio (hoje só teste de endpoint ou repo).

**Por que scope reduzido:** A6f.1 está em progresso paralelo e vai
reescrever `backend/app/api/pipeline.py` + dependências. Se A6e.3
tocasse Document/Task/Config (que usam `PipelineRun`, `StageReview`),
merge hell garantido. Os 3 agregados deste slice **não importam
`PipelineRun`** (verificado via grep) — rodam em isolamento.

**Agregados que ficam para slice seguinte (A6e.3b, pós-A6f.1 merge):**
ConfigBlob, Document, Task (os 3 que ou são o maior router, ou
referenciam pipeline).

---

## Regras inegociáveis

Do CLAUDE.md + ADR-101:

1. **1 endpoint = 1 use case.** Cada arquivo `application/<agg>/<use_case>.py` expõe 1 função `execute(command, deps) -> result`.
2. **Use case não conhece FastAPI.** Recebe DTOs + Protocols (repo, vault, etc.), retorna DTOs. Nunca `HTTPException`, `Depends`, `Request`. Erros como exceções de domínio tipadas.
3. **Repos via Protocol.** Use case recebe `FamilyMemberRepository` como param; teste injeta `FakeFamilyMemberRepository`. `@pytest.fixture` com repo fake — zero DB.
4. **Serviços computacionais permanecem** (ex.: `goal_compute_if.py`, `goal_compute_alocacao.py`) — são **domínio puro**, não viram use cases. Use case **chama** esses serviços.
5. **Funções 4-20 linhas, arquivos ≤500, nomes específicos** (§Code style). Use case típico tem ~15-40 linhas; se passa de 50, extraia helper de domínio.
6. **Dinheiro nunca é `float`** (ADR-090).
7. **Type hints obrigatórios** em API pública (parâmetros + retorno).
8. **Endpoint JSON mantém `response_model`** (ADR-109). Shim binário pode ficar até A6e.4 mexer nos routers.
9. **Preserve comentários existentes em refactor.**

---

## Estado atual — universo mapeado

**6 agregados com repo + DTO:** FamilyMember, Category, ConfigBlob, Document, Goal, Task.

**Seguro para A6e.3 slice inicial (zero import de `PipelineRun`):**

| Agregado | Service atual (linhas) | Router (linhas) | Use cases esperados |
|---|---|---|---|
| **FamilyMember** | `membership_service.py` 329 | `config.py` (parte) | 5-6 (create, list, update, delete, update_role, reset_surname) |
| **Category** | sem service (CRUD direto no router) | `config.py` (parte) | 4-5 (create, list, update, delete, bulk_create) |
| **Goal** | `goal_service.py` 412 + `goal_compute_*.py` (domínio puro) | `goals.py` 452 | 6-8 (create_goal_version por 4 tipos + list + project + compare) |

**Off-limits neste slice** (pipeline-related ou já com A6f.1):

```
backend/app/api/pipeline.py                    # A6f.1
backend/app/api/documents.py                   # usa PipelineRun
backend/app/api/tasks.py                       # tasks.py tem pipeline_task integration
backend/app/api/config.py (parte ConfigBlob)   # router maior; deixar para A6e.3b
backend/app/services/pipeline_service.py       # A6f.1
backend/app/services/document_processor.py     # A6f.1 adjacente
backend/app/tasks/pipeline_task.py             # A6f.1
backend/app/repositories/pipeline_artifact_repository.py  # A6f.1
```

**Router `config.py` (846 linhas):** **não** pode ser totalmente
migrado neste slice (inclui ConfigBlob). Estratégia: migrar **só** as
rotas de FamilyMember e Category que hoje vivem lá para
`backend/app/api/family_members.py` + `backend/app/api/categories.py`
(novos, finos); deixar resto do `config.py` intocado.

---

## Alvo estrutural — application layer

```
backend/app/application/
  __init__.py
  base/
    command.py           # @dataclass base Command (frozen, slots)
    result.py            # Result / DomainError base
    errors.py            # NotFound, Conflict, ValidationError tipadas
  family_member/
    __init__.py
    create_family_member.py
    list_family_members.py
    update_family_member.py
    delete_family_member.py
    update_family_member_role.py
    reset_family_surname.py
  category/
    __init__.py
    create_category.py
    list_categories.py
    update_category.py
    delete_category.py
    bulk_create_categories.py
  goal/
    __init__.py
    create_goal_version.py      # genérica, despacha por goal_type
    list_goal_versions.py
    get_active_goal.py
    project_if_trajectory.py    # chama goal_compute_if.compute_if_derived
    project_alocacao.py         # chama goal_compute_alocacao
    compare_goal_versions.py
```

**Protocolos** (contratos que o use case consome):

```python
# backend/app/application/family_member/_protocols.py
class FamilyMemberRepository(Protocol):
    async def list_by_workspace(self, workspace_id: str) -> list[FamilyMember]: ...
    async def get_by_id(self, workspace_id: str, member_id: str) -> FamilyMember | None: ...
    async def save(self, member: FamilyMember) -> None: ...
    async def delete(self, workspace_id: str, member_id: str) -> None: ...
```

(Nota: se `FamilyMemberRepository` já é concreta em `backend/app/repositories/`, ela **implementa** implicitamente este Protocol — duck typing. Protocol aqui é só para **documentação** e fakes.)

**Routers finos** (preparação para A6e.4):

```python
# backend/app/api/family_members.py (novo, fino)
@router.post("", response_model=FamilyMemberResponse, status_code=201)
async def create_family_member_endpoint(
    cmd: CreateFamilyMemberCommand,
    use_case: Annotated[CreateFamilyMember, Depends(get_create_family_member_use_case)],
) -> FamilyMemberResponse:
    try:
        return await use_case.execute(cmd)
    except FamilyMemberValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except WorkspaceNotFound:
        raise HTTPException(status_code=404)
```

---

## Targets — slice por agregado

### Slice 1 — FamilyMember (1 sessão)

**Por que primeiro:** agregado simples (329 linhas de service), 0 dependências de pipeline, 5-6 use cases diretos. Mostra o padrão para os demais.

**Passos:**

1. Criar `backend/app/application/base/` com `command.py`, `result.py`, `errors.py`. Um commit só, isolado.
2. Criar `backend/app/application/family_member/` com os 5-6 use cases. Cada um em arquivo próprio (4-30 linhas; orchestrator ≤20).
3. Testes puros em `backend/tests/application/family_member/test_*.py`:
   - `FakeFamilyMemberRepository` em `backend/tests/fakes/family_member.py`.
   - 1 arquivo de teste por use case (`test_create_family_member.py`), sem DB.
4. Criar `backend/app/api/family_members.py` (novo router fino, 6 endpoints).
5. Remover rotas de FamilyMember de `backend/app/api/config.py`. Preservar shim binário se necessário (`schemas/family_member.py` re-exporta command/response).
6. Regenerar OpenAPI: `make update-openapi-snapshot`. Verificar nenhum schema deletado — só renomes.

**Gate:**
- `pytest backend/tests/application/family_member/ -q` verde, **sem DB**.
- `pytest backend/tests/ -q` baseline + tests novos; zero regressão.
- `grep "select(FamilyMember" backend/app/api/` retorna zero.
- `backend/app/api/family_members.py` ≤120 linhas no final.
- OpenAPI snapshot diff é renomes + descrições, nunca drop de schema.

**Commit 1:** `refactor(backend): extract FamilyMember use cases + thin router (A6e.3 slice 1)`

### Slice 2 — Category (1 sessão curta)

**Por que segundo:** CRUD simples, zero orquestração. Replicar padrão de FamilyMember.

Mesmos passos, mesmos gates, mas sem `update_role` / `reset_surname`
(Category não tem). 4-5 use cases. `backend/app/api/categories.py` fino,
≤80 linhas. Remover rotas de Category de `config.py`.

**Commit 2:** `refactor(backend): extract Category use cases + thin router (A6e.3 slice 2)`

### Slice 3 — Goal (1 sessão grande, 6-8 use cases)

**Por que por último:** orquestração mais complexa (múltiplas versões,
4 tipos de goal, projeções), mas showcase do padrão.

**Nota:** `goal_compute_*.py` (alocacao, aporte, dolar, if_goal) são
**domínio puro** — não são use cases. Use case `project_if_trajectory`
**chama** `goal_compute_if.compute_if_derived(goal_params)`.

**Passos adicionais ao padrão:**
- `create_goal_version` é **genérica**: recebe `goal_type` + payload, despacha internamente. Validação de shape vem do DTO do mapper existente.
- Testes de projeção reutilizam goldens de `tests/fixtures/goals/` (se existem).
- `backend/app/api/goals.py` reescrito fino (452 → ~150 linhas).

**Gate extra:** goldens de goal.if / goal.alocacao / goal.aporte_mensal / goal.dolarizacao continuam verdes (`pytest backend/tests/test_goal_service.py -q` — existe e é ~412 linhas; se renomeado por A6g.5, siga o novo nome).

**Commit 3:** `refactor(backend): extract Goal use cases + thin router (A6e.3 slice 3)`

### Commit N+1 — docs (hotspot, ≤5min)

- `docs/CHANGELOG.md [Unreleased]`: A6e.3 slice 1+2+3 com números (use cases criados, linhas removidas de services fat, routers finos).
- `docs/BACKLOG.md`: `A6e.3` status ☐ → 🚧 parcial (3 agregados) ou ✅ se completou os 3.
- Considerar ADR-113 se emergir padrão novo (ex.: convenção de erros de domínio); opcional.

---

## Critérios de aceite (binários)

- [ ] `backend/app/application/{family_member,category,goal}/` existem com 15-20 use cases no total.
- [ ] `backend/app/application/base/` tem `Command`, `Result`, `DomainError` base.
- [ ] `backend/app/api/family_members.py` e `backend/app/api/categories.py` criados (routers finos).
- [ ] `backend/app/api/goals.py` encolheu de 452 para ≤200 linhas.
- [ ] `grep "select(FamilyMember\|select(Category\|select(Goal" backend/app/api/` = 0.
- [ ] `backend/tests/application/` existe com testes puros sem DB (fakes injetados).
- [ ] `backend/tests/fakes/` tem `FakeFamilyMemberRepository`, `FakeCategoryRepository`, `FakeGoalRepository`.
- [ ] `pytest backend/tests/application/ -q` verde em <5s (sem DB = rápido).
- [ ] `pytest backend/tests/ -q` baseline + novos tests; zero regressão.
- [ ] `make update-openapi-snapshot` — diff com renames `*UpsertRequest` → `*Command`, descrições novas; nenhum schema deletado.
- [ ] `backend/app/api/config.py` (846 linhas) perdeu rotas de FamilyMember + Category; resto intocado.
- [ ] Nenhum arquivo off-limits foi tocado (listado em §Estado atual).
- [ ] `pre-commit run --all-files` passa.

---

## Rollback criteria — ABORTE se

- `pytest backend/tests/ -q` regredindo >5 testes pós-refactor.
- `make update-openapi-snapshot` mostra schema deletado (frontend quebra).
- Pressão de delivery leva a "só aplica use case em 1 agregado" — abort parcial é pior que não começar; faça em branch feature, merge só completo.
- Você descobre que `goal_compute_*.py` importa `PipelineRun` ou `StageReview` (significa goal tocou pipeline e o slice não é mais seguro) — re-escopar.
- Lane A6f.1 commitou mudanças em `backend/app/schemas/pipeline.py` ou introduziu deps transversais que quebram seu repo layer; rebase e re-avaliar.

Em rollback: `git reset --hard origin/main` na branch local, anuncia, abre issue para o slice.

---

## Anti-patterns a evitar

- **Use case que importa FastAPI.** Se viu `from fastapi import` dentro de `backend/app/application/`, está errado. Exception handling volta para router.
- **Use case retornando Model do ORM.** Retorne DTO (Pydantic Response). Mapper converte.
- **Use case chamando session.commit().** Commit é responsabilidade do repo + outer (middleware). Use case é transação-naive.
- **Expandir escopo para Document/Task/Config.** Fora deste slice. Agende A6e.3b pós-A6f.1 merge.
- **Misturar serviço computacional (domain) com use case.** `goal_compute_if` continua puro; use case orquestra, não recalcula.
- **Criar Protocol redundante.** Se o repo concreto é suficiente para tipar, use ele direto; Protocol só vale pena quando existe mais de 1 implementação real (e fakes contam).
- **Reusar `*Request` como DTO do use case.** Use case recebe `*Command` (pode ser igual, mas nome diferente marca a fronteira). Mapper converte.
- **Commits que misturam agregados.** Cada slice = 1 agregado = 1 commit (+ 1 de testes, se grande). Rebase com 3 agregados num commit = impossível.

---

## Coordenação com outros agentes

Em paralelo a você, lanes ativas:

- `agent/a6f1-pipeline-service/*` — pipeline-as-service. **Precedência:** A6f.1 tem precedence sobre qualquer commit em arquivo pipeline-related. Seu slice é scope **não-pipeline**; zero overlap esperado. Se A6f.1 mergeia antes, seus 3 agregados não são afetados.
- `agent/a6g2-pipeline-style/*` — pipeline sweep, toca `scripts/`, `pipeline/`, `tests/fixtures/`. **Zero overlap.**
- `agent/a6g4-frontend-style/*` — 🚧 frontend sweep. **Zero overlap** com backend.
- `agent/a6g5-tests-sweep/*` — testes backend renomeados. **Overlap potencial** em `backend/tests/` (renames existentes vs seus tests novos). **Regra:** testes novos vão em `backend/tests/application/` (diretório novo) — sem conflito. Se A6g.5 renomear `backend/tests/test_goal_service.py` enquanto você escreve `test_create_goal_version.py`, commits não colidem (arquivos diferentes).

**Hotspots compartilhados:**

```bash
git fetch origin
git log -5 --oneline origin/main -- docs/CHANGELOG.md docs/BACKLOG.md
```

Se agente mergeou hotspot <30min, espere 2min, anuncie, commite docs no **mesmo turno** (≤5min).

**Sync periódico (sessão >1h):**

```bash
git fetch origin && git log --oneline HEAD..origin/main
# Se CLAUDE.md ou ADRs mudaram, releia antes de continuar
```

---

## O que este slice NÃO entrega (explicitar no CHANGELOG)

- **ConfigBlob use cases** — faz parte de `api/config.py` (846 linhas) junto de Institution configs, LLM configs, etc. Agregado grande; fica para A6e.3b quando A6e.4 (routers finos) destravar a decomposição de `config.py`.
- **Document + Task use cases** — bloqueados por A6f.1 (pipeline refactor tocando document_processor e pipeline_task). A6e.3b pós-merge.
- **Domain events tipados** — A6e.events (ex-`A6e.6`). Use cases deste slice não emitem eventos (ainda).
- **Migração /api/v1/ prefix** — A6e.5. Manter rotas em `/` durante este slice.
- **Enforcement automatizado** (teste AST contra `select(Model` em routers) — A6g.6.

---

## Referências

- [ADR-101](../DECISIONS.md) — R15 application layer (use cases)
- [BACKLOG §A6e](../BACKLOG.md) — per-aggregate entregas + próximos passos
- Slice modelo (per-aggregate FamilyMember): commit `c84af46`, `2d9074b`, `13ece89`, `4167fa5` (branch `a6e/family-member-slice`, ver BACKLOG)
- Prompts paralelos: [track_a6g2](track_a6g2_pipeline_style_sweep.md), [track_a6g4](track_a6g4_frontend_style_sweep.md), [track_a6f1](track_a6f1_pipeline_service.md), [track_a6g5](track_a6g5_tests_sweep.md)
