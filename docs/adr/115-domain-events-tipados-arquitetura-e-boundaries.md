---
id: ADR-115
type: adr
title: "Domain events tipados: arquitetura e boundaries (A6e.events)"
status: Decidido
phase: "A6e.events"
date: "2026-04-22"
relates_to: []
supersedes: []
superseded_by: []
aliases: ["ADR 115"]
tags:
  - area/backend
  - area/persistence
  - area/pipeline
  - status/decidido
  - type/adr
size_lines: 134
---

# ADR-115 — Domain events tipados: arquitetura e boundaries (A6e.events)

**Status:** Decidido (A6e.events) • **Data:** 2026-04-22

**Contexto:** A6e.3/.3b fecharam a application layer — 47 use cases
limpos, zero side-effect inline. Side-effects transversais (audit log,
notificações, cache invalidation futura) continuam dispersos: `audit_log()`
é chamado inline em ~5 routers; notificações de prazo vivem em polling
cron (`scan_and_create_notifications`) desconectado do lifecycle da
Task. F7B.5 vai consumir audit log completo em produção — formalizar o
padrão antes de espalhar reduz retrabalho.

`backend/app/services/events.py` já existe mas é Redis pub/sub para
**progresso de pipeline stages** (publish_stage_started/completed) —
escopo diferente; tentar unificar cria acoplamento inútil.

Três alternativas consideradas:

1. **Sem eventos, side-effects inline continuam** — rejeitada. Audit em
   ~15 call-sites hoje cresce quadraticamente; cada novo agregado
   duplica o padrão. Notificação de prazo permanece órfã do ciclo de
   Task (cron só vê snapshot periódico).
2. **Event store persistido (event sourcing)** — rejeitada por over-engineering.
   Não há necessidade de reconstrução de agregados por replay; só
   desacoplar side-effect do use case. Event sourcing completo exigiria
   refactor de repositories (estado vs. log), impacto maior que o
   ganho atual.
3. **Handlers async pós-commit por padrão (Celery)** — rejeitada como
   default. Handler que escreve audit precisa de atomicidade com o use
   case (commit falha → audit não fica órfão). Async post-commit volta
   como segundo modo quando houver caso concreto (email, WebSocket
   broadcast); ponte `enqueue_async` fica como stub.

**Decisão:** introduzir camada `backend/app/events/` com:

- **`Event` base**: `@dataclass(frozen=True, slots=True, kw_only=True)`
  com `event_id` (UUID hex), `occurred_at` (tz-aware UTC),
  `aggregate_id/type`, `workspace_id`. Subclasses adicionam payload
  tipado; imutabilidade garantida por `frozen` + `slots`.
- **Registro estático** via `@register_handler(EventClass)` — decorator
  roda em tempo de import (singleton idempotente, ADR-111 permite).
  `backend.app.events.handlers.__init__` importa cada módulo de
  handler explicitamente; zero glob auto-discovery.
- **Dispatch síncrono por padrão**: `dispatch_sync(event, deps)` roda
  handlers na transação do caller. Falha propaga → caller decide
  rollback. Handlers async são aguardados (`inspect.isawaitable`).
- **Deps injetados explicitamente** via `EventHandlerDeps` (TypedDict
  com `total=False`): dispatcher passa o mapping; cada handler pulls
  o que precisa (`deps["db"]`). Nada de context var global (ADR-111).
- **`enqueue_async` stub**: ponte para Celery / SQLAlchemy
  `after_commit` listener; levanta `NotImplementedError` até slice
  dedicado ativar (quando aparecer handler que escreva fora do DB).
- **Handlers são funções puras** sem estado interno — nenhum `_cache`,
  `@lru_cache` ou counter compartilhado (ADR-111 stateless rigoroso).

**Entregue na lane A6e.events (3 slices + docs):**

- **Slice 1 (infra):** base/registry/dispatcher/protocols + 18 unit
  tests (frozen, slots, UUID, ordem determinística, propagação de
  exceção, injeção de deps).
- **Slice 2 (AuditLogEvent):** `AuditLogEvent` +
  `FamilyMemberCreatedEvent` + handler `write_audit_entry` /
  `audit_family_member_created` (traduz agregado → audit). Migra
  `application/family_member/create_family_member.py` para emitir
  `FamilyMemberCreatedEvent` após `repo.create()`. Router passa
  `db` + `current_user.id` explicitamente.
- **Slice 3 (Task events):** `TaskCreatedEvent` + `TaskUpdatedEvent` +
  handler `on_task_created` / `on_task_updated` (cria Notification
  quando prazo está no horizonte). Flag
  `MATHOMS_USE_EVENT_DRIVEN_TASK_NOTIFICATIONS` default False —
  `scan_and_create_notifications` cron continua fonte única até
  validação humana (A6e.events-followup).

**Consequências:**

- ✅ Use cases emitem eventos e ignoram handlers — zero import de
  audit/notification service na application layer. Novos agregados
  seguem mesmo padrão.
- ✅ Atomicidade preservada em repos caller-owns-commit (Task): task +
  notification na mesma txn; rollback descarta ambos.
- ✅ Handler do tipo errado explode ruidoso (TypeError por kwargs); sem
  fallback silencioso. Registro explícito → auditar handlers é `grep
  @register_handler`.
- ✅ Novo agregado que precisa de audit ganha `XCreatedEvent` + handler
  que traduz para `AuditLogEvent`; zero código duplicado em routers.
- ⚠️ **Atomicidade parcial** em repos legados que commitam internamente
  (`FamilyMemberRepository.create()` faz `session.commit()`). Audit
  vive em transação separada que o use case fecha logo depois; falha
  no handler desfaz o audit mas deixa o membro committed. Aceito como
  limitação temporária — fechar quando repositories não-Task migrarem
  para caller-owns-commit (R14). Testes cobrem rollback isolado do
  handler.
- ⚠️ Registro global `_HANDLERS` é estado de módulo — considerado
  singleton idempotente (populado em import time, imutável em runtime
  de produção). Testes usam `clear_handlers` + save/restore em
  fixture para não apagar registros reais.
- ⚠️ ~14 call-sites de `audit_log()` inline em `backend/app/api/` ainda
  não foram migrados — tarefa dedicada "A6e.events-migration" depois
  de padrão validado.
- ❌ Documentação da descoberta de handler é manual (precisa editar
  `handlers/__init__.py`). Aceito para rejeitar descoberta automática
  por glob, que esconde side-effects de registro.

**Escopo deferido (follow-ups explícitos):**

- **Migração dos ~14 `audit_log()` call-sites** restantes em
  `backend/app/api/*.py` — tarefa dedicada A6e.events-migration.
- **Handlers async (Celery dispatch, email, broadcast WS)** — quando
  houver caso concreto; `enqueue_async` stub já sinaliza o caminho.
- **Event store persistido** (event sourcing) — explicitamente fora de
  escopo; eventos são ephemeral, vivem só durante dispatch.
- **Remoção do cron `scan_and_create_notifications`** — após A6e.events-
  followup ativar `MATHOMS_USE_EVENT_DRIVEN_TASK_NOTIFICATIONS=True`
  em produção e validar por 2+ semanas.
- **Repo FamilyMember/outros não-Task migrarem para caller-owns-commit**
  (R14) — fecha a atomicidade parcial documentada acima.

**Nota de naming** (ADR-101): `R17` originalmente referenciava `A6e.6`
(domain events). Em 2026-04-22 a lane foi renomeada `A6e.6 → A6e.events`
para evitar colisão histórica com 5 commits de `(A6e.6)` que eram o
slice Goal do track per-aggregate. ADR-101 R17 aponta para a nova
sub-fase; commits desta lane filtráveis por `git log --grep "A6e.events"`.

**Artefatos:**

- `backend/app/events/{base,registry,dispatcher,protocols,domain,__init__}.py`
- `backend/app/events/handlers/{audit_log_handler,task_notification_handler}.py`
- `backend/tests/events/` — 32 testes (unit + integration DB + flow via API)
- `backend/app/core/config.py` — flag `USE_EVENT_DRIVEN_TASK_NOTIFICATIONS`
- `backend/app/application/family_member/create_family_member.py` — emite evento
- `backend/app/application/task/{create_task,update_task}.py` — emitem eventos
- `backend/app/api/family_members.py` — injeta `db` + `actor_user_id`
