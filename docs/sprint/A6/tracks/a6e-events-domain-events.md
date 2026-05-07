---
id: TRACK-a6e-events-domain-events
type: track
title: "Track A6e.events — Domain events tipados (ADR-101 R17)"
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

# Track A6e.events — Domain events tipados (ADR-101 R17)

> **Lane ID:** A6e.events (**ex-`A6e.6`** — renomeada em 2026-04-22 para evitar colisão com commits históricos do Goal slice)
> **Branch prefix:** `agent/a6e-events/*`
> **Depende de:** A6e.3 ✅ + A6e.3b ✅ (todos os use cases da application layer já existem; eventos vão emitir deles)
> **Paralelo com:** A6e.4 (🚧 thin routers; zero conflito — eventos vivem em use cases, não routers), A6g.2/.4/.5/.7 ✅, A6f.1 ✅
> **Conflita com:** commits simultâneos em `backend/app/application/**/*.py` (use cases ganham `emit(event)` nesta lane). A6e.4 não toca use cases (só routers) — coexiste. Se A6e.4 ainda estiver ativa, merge em sequência via rebase incremental.
> **Onda:** 2
> **Índice de prompts:** [README.md](README.md)
> **Fonte de verdade:** [ADR-101 R17](../DECISIONS.md) · [CLAUDE.md §Code style](../../CLAUDE.md#code-style) · [BACKLOG §A6e](../BACKLOG.md)

> **Objetivo:** introduzir camada de **domain events tipados** em
> `backend/app/events/` — base class `Event` + `register_handler` +
> dispatcher síncrono (em transação) e assíncrono (pós-commit). Use cases
> emitem eventos em vez de chamar `audit_log()`, `create_notification()`,
> `cache.invalidate()` inline. **Não** reescreve a camada de pub/sub de
> pipeline (`backend/app/services/events.py` — aquela é Redis pub/sub
> para progress de stages; escopo separado).

---

## Atenção — ambiguidade histórica

O ID `A6e.6` foi usado no passado (2026-04-21) para rotular o **slice
Goal** do track per-aggregate (`backend/app/repositories/goal_repository.py`
+ DTOs + mapper + testes). 5 commits antigos carregam `(A6e.6)` na message:

```
888ce45 docs(a6e.6): CHANGELOG + BACKLOG marcam slice Goal ✅
632edf7 docs(api): openapi snapshot — A6e.6
ad6ae5f test(backend): Goal DTO mapper + repository (A6e.6 — 28 testes)
db34363 backend(api): goals.py usa GoalRepository + DTOs (A6e.6)
6bc4754 backend(dto): goal response/command/compute/mapper — 4 tipos (A6e.6 — ADR-101)
```

**Por isso esta lane foi renomeada `A6e.6 → A6e.events`** em 2026-04-22.
Ao pesquisar histórico, filtre: `git log --grep "A6e.events"` retorna
**apenas** commits desta lane. ADR-101 R17 foi atualizada com a renomeação.

---

## Por que esta lane agora

1. **A6e.3 ✅ e A6e.3b ✅** entregaram use cases para todos os 6 agregados (FamilyMember · Category · Goal · ConfigBlob · Document · Task). Use cases hoje são **limpos** — zero side-effect inline. Campo verde para eventos.
2. **Audit log é o caso de uso número 1 hoje:** `backend/app/services/audit.py::audit_log(db, ...)` é chamado **inline em endpoints** (~15 call-sites). Side-effect acontece **antes** do `db.commit()` — se commit falhar, audit fica órfã. Eventos resolvem (handler roda na mesma transação).
3. **Task notifications** são cron polling hoje (`task_notification_service.scan_and_create_notifications()`). Pode virar handler de `TaskCreated`/`TaskUpdated` emit em use case.
4. **F7B.5 audit log completo** (produção) será consumidor do event system — entregar A6e.events antes de F7B reduz retrabalho.
5. **ADR-111 stateless rigoroso** — handlers bem desenhados não quebram; handlers mal desenhados viram estado mutável. Formalizar o padrão agora (em ADR + testes) antes de espalhar.

---

## Regras inegociáveis

Do CLAUDE.md + ADR-101 R17 + ADR-111:

1. **`backend/app/events/` é greenfield.** Crie a estrutura de dentro para fora: base → registry → domain events tipados → handlers → integração em use cases.
2. **`Event` é imutável.** `@dataclass(frozen=True, slots=True)` + `field(default_factory=...)` para `event_id` (UUID) e `occurred_at` (UTC). Nunca mutar após criação.
3. **Handlers são funções puras + Protocol-typed** no dispatcher. Registro explícito via decorator `@register_handler(EventClass)` em módulo de inicialização; nada de descoberta automática fragil.
4. **Dispatch síncrono por padrão** — handler roda **dentro da transação** do use case. Falha do handler faz `rollback` da transação toda. **Nunca** `asyncio.create_task(...)` ou `BackgroundTasks` dentro de handler síncrono (ADR-111 proíbe).
5. **Dispatch assíncrono via Celery** para handlers que escrevem fora do DB (Redis cache, broadcast WS, envio de email). Celery worker tem sua própria transação; handler enqueue task em `after_commit` listener.
6. **Stateless rigoroso** (ADR-111): handlers **não guardam estado** entre invocações. Nenhum `_cache = {}` em module-level, nenhum `@lru_cache` mutável, nenhum counter compartilhado.
7. **Zero emit em routers.** Eventos emitidos **apenas** em use cases (`backend/app/application/<agg>/<use_case>.py`). Router continua thin (ADR-101 R16).
8. **Audit log migra gradualmente** — este slice cobre a infra + **1 caso concreto de migração** (ex.: `AuditLogEvent` emit em `CreateFamilyMember` com handler `AuditLogHandler`). Outros call-sites de `audit_log()` ficam para slice seguinte.
9. **Funções 4-20 linhas, arquivos ≤500** (§Code style). Event classes <10 linhas cada.
10. **Type hints obrigatórios.** Sem `Any` em assinatura de handler — `Callable[[EventType], Awaitable[None]]` para async ou `Callable[[EventType], None]` para sync.

---

## Estado atual — mapeado

**Já existe no repo:**

| Arquivo | Linhas | Função |
|---|---|---|
| `backend/app/services/events.py` | ~63 | **Redis pub/sub apenas para pipeline stages** (publish_stage_started, publish_stage_completed). NÃO reusar — escopo diferente (pipeline progress, não domain events). |
| `backend/app/services/audit.py` | 152 | `audit_log()` / `audit_log_sync()` — chamados inline em endpoints. **Candidato 1** a virar handler. |
| `backend/app/services/audit_service.py` | 86 | Convenção de action strings. Reutilizar. |
| `backend/app/models/audit_log.py` | — | AuditLog ORM model. Reutilizar. |
| `backend/app/services/task_notification_service.py` | 148 | `scan_and_create_notifications()` — **polling cron**, não event-driven. **Candidato 2** a virar handler de `TaskCreated`/`TaskUpdated`. |
| `backend/app/application/base/errors.py` | — | `DomainError` hierarchy (`NotFoundError`, `ConflictError`, `ValidationError`). Reutilizar — eventos podem ter campos `error: DomainError | None`. |
| `backend/app/application/{family_member,category,goal,config_blob,document,task}/**` | — | Use cases limpos. **Emitem eventos** após este slice. |

**Não existe (greenfield):**

- `backend/app/events/` (diretório inteiro)
- `Event` base class tipada
- `register_handler` / dispatcher
- Handlers concretos (audit, notifications)
- ADR-115 formalizando a arquitetura

---

## Alvo estrutural

```
backend/app/events/
  __init__.py            # registro de handlers na inicialização
  base.py                # Event (frozen dataclass) + type registry
  registry.py            # register_handler decorator + _HANDLERS dict
  dispatcher.py          # dispatch_sync() + dispatch_async_after_commit()
  domain.py              # event classes tipadas (AuditLogEvent, TaskCreatedEvent, ...)
  handlers/
    __init__.py          # registros explícitos (@register_handler decorators importados)
    audit_log_handler.py
    task_notification_handler.py
  protocols.py           # HandlerProtocol, DispatcherProtocol (para injeção em use cases)
```

### `base.py` — `Event` base class

```python
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4

@dataclass(frozen=True, slots=True)
class Event:
    """Base class para domain events tipados (ADR-101 R17)."""
    event_id: str = field(default_factory=lambda: uuid4().hex)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    aggregate_id: str | None = None
    aggregate_type: str | None = None
    workspace_id: str | None = None
```

### `registry.py` — type-safe handler registration

```python
from collections.abc import Callable
from typing import Protocol, TypeVar

EventT = TypeVar("EventT", bound=Event)
SyncHandler = Callable[[EventT], None]
AsyncHandler = Callable[[EventT], Awaitable[None]]

_HANDLERS: dict[type[Event], list[SyncHandler | AsyncHandler]] = {}

def register_handler(event_class: type[EventT]):
    """Decorator — registra handler para type específico."""
    def decorator(handler: SyncHandler | AsyncHandler) -> SyncHandler | AsyncHandler:
        _HANDLERS.setdefault(event_class, []).append(handler)
        return handler
    return decorator
```

### `dispatcher.py` — síncrono (txn) + async (post-commit)

```python
async def dispatch_sync(event: Event) -> None:
    """Roda handlers **dentro da transação atual**. Falha propaga → rollback."""
    for handler in _HANDLERS.get(type(event), []):
        result = handler(event)
        if asyncio.iscoroutine(result):
            await result

def enqueue_async(event: Event) -> None:
    """Handler assíncrono pós-commit (Celery ou after_commit SQLAlchemy listener).
    Escopo pode ficar para slice seguinte — bare-bones com Celery task é suficiente."""
    ...
```

### `domain.py` — event classes tipadas

Começar com 3 eventos concretos:

```python
@dataclass(frozen=True, slots=True)
class AuditLogEvent(Event):
    action: str
    resource_type: str
    resource_id: str | None = None
    actor_user_id: str | None = None
    details: dict[str, Any] | None = None

@dataclass(frozen=True, slots=True)
class TaskCreatedEvent(Event):
    task_id: str
    deadline_at: datetime | None = None
    assignee_user_id: str | None = None

@dataclass(frozen=True, slots=True)
class FamilyMemberCreatedEvent(Event):
    member_id: str
    member_name: str  # masked em logs (ADR-110)
```

### `handlers/audit_log_handler.py` — primeiro handler concreto

```python
@register_handler(AuditLogEvent)
async def write_audit_entry(event: AuditLogEvent, db: AsyncSession) -> None:
    """Grava AuditLog no DB — mesma transação do use case."""
    entry = AuditLog(
        action=event.action,
        resource_type=event.resource_type,
        resource_id=event.resource_id,
        workspace_id=event.workspace_id,
        actor_user_id=event.actor_user_id,
        details=event.details,
        created_at=event.occurred_at,
    )
    db.add(entry)
    # commit é do caller (use case)
```

**Desafio de injeção:** handler precisa da `AsyncSession` atual. Opções:
- (A) Context var: use case pushes session no context, handler pull. Simples mas acopla.
- (B) Pass explicit: `dispatch_sync(event, deps={"db": session})`. Explícito, mais verboso.
- (C) `register_handler(AuditLogEvent, needs_db=True)` flag + dispatcher injeta automaticamente.

**Recomendação:** (B) para este slice (explícito > mágico; CLAUDE.md §Dependências).

### Integração em use case — exemplo

**Antes** (em endpoint, inline):

```python
# backend/app/api/family_members.py (hoje, inline)
@router.post("")
async def create_family_member(...):
    member = await use_case.execute(cmd)
    await audit_log(db, action="family_member.created", resource_id=member.id, ...)
    return family_member_to_response(member)
```

**Depois** (use case emite evento):

```python
# backend/app/application/family_member/create_family_member.py
async def execute(self, cmd: CreateFamilyMemberCommand) -> FamilyMember:
    member = FamilyMember(...)
    await self._repo.save(member)
    await dispatch_sync(FamilyMemberCreatedEvent(
        member_id=member.id, member_name=member.name,
        aggregate_id=member.id, aggregate_type="family_member",
        workspace_id=cmd.workspace_id,
    ), deps={"db": self._db})
    return member

# + handler audit_log_handler registrado:
@register_handler(FamilyMemberCreatedEvent)
async def on_family_member_created(event: FamilyMemberCreatedEvent, db: AsyncSession) -> None:
    audit = AuditLogEvent(
        action="family_member.created",
        resource_type="family_member",
        resource_id=event.member_id,
        workspace_id=event.workspace_id,
    )
    await write_audit_entry(audit, db)
```

**Router** permanece thin, agora sem `audit_log()` inline.

---

## Targets — 4 slices

### Slice 1 — infra base (`backend/app/events/`)

- `base.py`, `registry.py`, `dispatcher.py`, `__init__.py`, `protocols.py`
- Testes unitários puros: registro de handler, dispatch sync ordena pelo tempo de registro, exceção em handler propaga, tipo errado levanta TypeError
- ADR-115 draft (será consolidada em commit separado)

**Commit 1:** `feat(events): base Event + register_handler + dispatcher (A6e.events · slice 1 · ADR-101 R17)`

### Slice 2 — `AuditLogEvent` + `AuditLogHandler` ponta-a-ponta

- `domain.py` com `AuditLogEvent`
- `handlers/audit_log_handler.py` — grava `AuditLog` model (reutiliza infra existente em `services/audit.py`)
- Migrar **1 use case** (sugestão: `CreateFamilyMember`) de `audit_log()` inline para `dispatch_sync(AuditLogEvent, ...)`
- Testes: integração com DB real (SQLite in-memory), cobre rollback (handler falha → transação toda desfaz), cobre audit entry gravada no happy path
- **Não migrar** os outros ~14 call-sites de `audit_log()` neste slice — fica para tarefa dedicada após padrão validado

**Commit 2:** `feat(events): AuditLogEvent + handler + migra CreateFamilyMember (A6e.events · slice 2)`

### Slice 3 — `TaskCreatedEvent` + `TaskUpdatedEvent` + migração parcial

- Adicionar events em `domain.py`
- `handlers/task_notification_handler.py` — substitui `scan_and_create_notifications()` polling por handler reativo em `TaskCreatedEvent`/`TaskUpdatedEvent`
- Migrar use cases: `CreateTask`, `UpdateTask` em `application/task/` emitem eventos
- **Manter cron antigo em paralelo** (com flag `MATHOMS_USE_EVENT_DRIVEN_TASK_NOTIFICATIONS=false` default) até próximo slice validar em produção
- Testes: use case emite evento; handler cria Notification; round-trip via `pytest backend/tests/application/task/`

**Commit 3:** `feat(events): TaskCreated/Updated + task notification handler (A6e.events · slice 3)`

### Slice 4 — ADR-115 + CHANGELOG + BACKLOG (docs hotspot, ≤5min)

- ADR-115 formaliza arquitetura: Event imutável, registry explícito, sync-in-txn default, stateless
- CHANGELOG [Unreleased]: entrada A6e.events com deltas (3 events, 2 handlers, 3 use cases migrados, ADR-115)
- BACKLOG §Sprint A6: A6e.events ☐ → 🚧 parcial (se slices 2+3 fizeram migração mínima) ou ✅ (se todos os use cases migrados — improvável neste slice)
- Diagrama de ondas se necessário (A6e trilho chega perto do fim)

**Commit 4:** `docs(a6e.events): ADR-115 domain events + CHANGELOG + BACKLOG`

### Fora de escopo (explicitar no CHANGELOG)

- **Migração dos ~14 call-sites restantes de `audit_log()` inline** — tarefa dedicada "A6e.events-migration" após validar padrão.
- **Handlers async pós-commit (Celery dispatch, Redis broadcast)** — adicionar quando houver caso concreto; Slice 1 deixa a ponte pronta (`enqueue_async` stub).
- **Event sourcing / event store persistido** — não é escopo; eventos aqui são ephemeral (vivem só enquanto o dispatch roda).
- **WebSocket broadcast via event** — possível futuro mas `services/events.py` existente resolve o caso pipeline; WebSocket de domínio fica para slice dedicado.

---

## Sequência de execução

### 1. Setup

```bash
git fetch origin
git worktree list                           # confirma zero worktree agent/a6e-events-*
git for-each-ref --sort=-committerdate \
  --format='%(committerdate:iso) %(refname:short)' \
  refs/remotes/origin/agent/ | head -15
# Nota: branch prefix é a6e-events (não a6e.events — dot não é valid em ref)
git checkout -b agent/a6e-events/$(date +%Y%m%d-%H%M)
```

### 2. Baseline

```bash
pytest backend/tests -q 2>&1 | tail -3      # anotar N passed
grep -rnE "await audit_log\(" backend/app/ | wc -l   # baseline de call-sites inline
```

### 3. Slices 1 → 4 na ordem acima

Cada slice: commit atômico, gate verde antes do próximo. **Nunca** misture slice 1 (infra) com slice 2 (migração). Rollback limpo exige isolamento.

### 4. Gates de push

```bash
pre-commit run --all-files
pytest backend/tests -q                      # zero regressão + novos tests passando
make update-openapi-snapshot                 # sem mudanças esperadas (eventos não expõem schema HTTP)

git fetch origin
BEHIND=$(git rev-list --count HEAD..origin/main)
[ "$BEHIND" -gt 0 ] && git rebase origin/main && pytest backend/tests -q

git push origin HEAD:main
```

---

## Critérios de aceite (binários)

- [ ] `backend/app/events/` existe com: `base.py`, `registry.py`, `dispatcher.py`, `domain.py`, `protocols.py`, `__init__.py`, `handlers/__init__.py` + 2 handlers.
- [ ] `Event` é `@dataclass(frozen=True, slots=True)` com `event_id` (UUID), `occurred_at` (tz-aware UTC), `aggregate_id/type`, `workspace_id`.
- [ ] `register_handler(EventClass)` funciona como decorator; dispatcher dispara handlers registrados na ordem de registro.
- [ ] 3 event classes concretas: `AuditLogEvent`, `TaskCreatedEvent`, `TaskUpdatedEvent` (ou subset + 1).
- [ ] 2 handlers concretos: `write_audit_entry` + `task_notification_handler`.
- [ ] **Pelo menos 1 use case migrado** de side-effect inline para `dispatch_sync(event, ...)`.
- [ ] Testes: base + registry + dispatcher (unit puro); + integration handler + DB; + use case migration (antes/depois mesmo comportamento observável via DB).
- [ ] `grep -rn "@lru_cache\|BackgroundTasks\|asyncio.create_task" backend/app/events/` = zero (ADR-111 stateless).
- [ ] `grep -rn "await audit_log(" backend/app/application/` = zero (use cases não chamam audit inline; eventos fazem).
- [ ] ADR-115 escrita em `docs/DECISIONS.md`.
- [ ] CHANGELOG + BACKLOG atualizados.
- [ ] `pre-commit run --all-files` passa.

---

## Rollback criteria — ABORTE se

- `pytest backend/tests -q` regredir em ≥2 tests (indica que o dispatcher está reordenando side-effects de forma incompatível).
- Algum use case migrado em slice 2/3 muda comportamento observável (audit entry chegou antes do refactor, não chega depois — indica quebra na propagação da sessão para o handler).
- Tests novos são flaky (ordem de registro de handlers importa — se flaky, revisitar slice 1 até determinístico).
- `make update-openapi-snapshot` mostra schema mudado (lane não deveria mexer em contratos HTTP).
- `dev/check_pipeline_boundaries.py` reporta `pipeline/**/*.py` importando `backend.app.events` (pipeline não pode importar framework; se aconteceu, quebrou ADR-097).

Em rollback: `git reset --hard origin/main` na branch; anuncie motivo + hash offender; documentação "tentativa X — rollback" no CHANGELOG se algo ficou committed.

---

## Anti-patterns a evitar

- **Descoberta automática de handlers** via glob/import-all. Fragil, esconde side-effects de registro. **Explicite** com `@register_handler(EventClass)` + import do módulo em `events/__init__.py`.
- **Handler assíncrono escrevendo no DB "em background".** Rompe transactional consistency. Handlers que precisam de DB rodam **síncronos na transação do use case**.
- **Event mutável.** Se handler modificar o evento, outros handlers veem o estado mutado — debugging pesadelo. `frozen=True` garante imutabilidade.
- **Emitir evento de dentro de handler.** Cria cascata difícil de rastrear; handler escreve no DB ou enfileira task, não emite novo evento (se precisar, use case que recebe resultado do handler decide).
- **Passar `AsyncSession` via context var global.** ADR-111 stateless rigoroso — qualquer módulo-level mutable é risco. Injeção explícita via `deps={...}` no dispatch.
- **Migrar todos os 14 `audit_log()` call-sites neste slice.** Escopo creep. Este slice prova o padrão; migração em massa é tarefa dedicada.
- **Criar `AuditLogHandler` classe com `__init__`** que guarda `db`. Handler é função pura; deps via parâmetro no call, não estado.
- **Reusar `backend/app/services/events.py`** que é Redis pub/sub de pipeline progress. Escopo diferente; tentar unificar cria acoplamento inútil.

---

## Coordenação com outros agentes

| Lane | Status | Risco |
|---|---|---|
| **A6e.4** thin routers | 🚧 ativo (2/14 done + AST) | **Baixo** — A6e.4 toca routers, esta lane toca use cases + novo `events/`. Overlap potencial apenas se A6e.4 mover lógica de router que chama `audit_log()` para dentro de use case — rebase incremental resolve. |
| **A6e.3b** use cases | ✅ mergeada | Baseline: todos os 6 agregados com use cases limpos. Seus use cases são o target desta lane. |
| **A6-human** smoke | ☐ gate humano | **Cuidado:** migrar `audit_log()` inline pode afetar checks de audit no smoke test. Migrar apenas 1 use case em slice 2 e validar antes de expandir. |
| **F7B.5** audit log completo | ⏸ F7B | Consumidor futuro do event system. Antecipe padrão agora. |

**Hotspots compartilhados** (`docs/CHANGELOG.md`, `docs/BACKLOG.md`, `docs/DECISIONS.md`):

```bash
git fetch origin
git log -5 --oneline origin/main -- docs/CHANGELOG.md docs/BACKLOG.md docs/DECISIONS.md
```

Se agente mergeou hotspot <30min, espere 2min, anuncie, commite docs no **mesmo turno** (≤5min). ADR-115 é commit separado de código; BACKLOG/CHANGELOG em outro commit ainda separado.

**Sync periódico (sessão >1h):**

```bash
git fetch origin && git log --oneline HEAD..origin/main
# Se A6e.4 merge, pode ter tocado use cases que você já emitiu evento de — rebase e reconcilie
```

---

## O que esta lane NÃO entrega

- **Migração completa de `audit_log()` inline** — ~14 call-sites restantes em `backend/app/api/*.py`. Tarefa dedicada pós-A6e.events.
- **Handlers assíncronos ricos** (Celery, Redis broadcast, email send) — stub pronto, implementação quando houver caso concreto.
- **Event store persistido** (event sourcing) — explicitamente fora de escopo; ADR-115 diz eventos são ephemeral.
- **Remoção de `scan_and_create_notifications()` polling cron** — flag `MATHOMS_USE_EVENT_DRIVEN_TASK_NOTIFICATIONS` deixa os dois caminhos coexistindo até validação em prod.
- **Integração com pipeline events** (`services/events.py`) — escopo diferente; não unificar por ora.

---

## Referências

- **ADR-101 R17** — Domain events tipados (sub-fase `A6e.events`, ex-`A6e.6`)
- **ADR-111** — Stateless rigoroso (handlers não guardam estado)
- **ADR-097** — Extract-then-refactor (padrão seguido: primeiro infra, depois migração gradual)
- [CLAUDE.md §Code style](../../CLAUDE.md#code-style) — funções 4-20 linhas, dataclasses frozen, sem `Any` em assinatura
- [BACKLOG §A6e](../BACKLOG.md) — trilho completo (hoje: use cases ✅, routers 🚧, eventos ☐)
- Prompts paralelos: [track_a6e4](track_a6e4_thin_routers.md)
- Existing infra reutilizável: `backend/app/services/audit.py`, `services/audit_service.py`, `models/audit_log.py`, `services/task_notification_service.py`
- Existing **não** reutilizável (escopo diferente): `backend/app/services/events.py` (Redis pub/sub pipeline)
