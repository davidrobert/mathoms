---
id: A6e
type: lane
title: "DDD/SOLID no backend API (ADR-101, R12-R17)"
sprint: A6
status: in_progress
branch_slug: a6e5-document
adrs: ["[[ADR-114]]", "[[ADR-115]]"]
depends_on: []
parallel_with: []
tags:
  - type/lane
  - sprint/a6
  - status/in-progress
---


# A6e — DDD/SOLID no backend API (ADR-101, R12-R17)


| # | Sub-fase | Entrega | Esforço | Status |
| --- | --- | --- | --- | --- |
| A6e.1 | Repos por aggregate | User, Workspace, Document, Goal, PipelineRun, Task, Notification, Invitation, AuditLog repositories; `grep sqlalchemy backend/app/api/` = zero | 1-2 sessões | 🚧 parcial — **FamilyMember + Category + ConfigBlob + Document + Goal + Task** ✅ |
| A6e.2 | DTO ↔ Model | `schemas/dto/<aggregate>/response.py` + `command.py` + `query.py` + `mapper.py`; zero `Model.from_orm` em endpoints | 1 sessão | 🚧 parcial — **family_member + category + config_blob + document + goal + task** ✅ |
| A6e.3 | Application layer | `backend/app/application/<aggregate>/<use_case>.py`; 1 endpoint = 1 use case; testável sem DB via fakes | 2 sessões | 🚧 parcial — **FamilyMember + Category + Goal** (22 use cases) ✅ 2026-04-21 |
| A6e.3b | Use cases ConfigBlob + Task + Document | 3 agregados restantes + sub-agregados Task; Protocol + fakes; composites com storage/audit deferidos ao router | 2 sessões | ✅ 2026-04-22 — 25 use cases (6 ConfigBlob + 13 Task + 6 Document) + 61 testes puros; total application layer = 47 use cases em 6 agregados; `pytest backend/tests -q` 1054 passed |
| A6e.3c | Sweep `dict[str, Any]` → tipado em DTOs não-OPAQUE (follow-up ADR-114) | 4 arquivos em `schemas/dto/{family_member/*, category/mapper.py}`; promove `LEGACY_FILES` → `CLEAN_FILES` em `test_no_any_in_boundary.py` | 0.5 sessão | ✅ 2026-04-22 (`35c7502`) |
| A6e.4 | Routers finos | Refactor 4900→800 linhas (17 routers × ≤50); teste AST enforça | 1-2 sessões | ✅ 2026-04-22 (fase 4a 14/14 + fase 4b 3/3) |
| A6e.5 | Versionamento `/api/v1/` | Prefixo + aliases durante window; OpenAPI 3.1 versionado; `lib/api.ts` atualizado | 1 sessão | ✅ 2026-04-22 — rotas canônicas `/api/v1/*`; `LegacyApiDeprecationMiddleware` anuncia Sunset no `/api/*` (RFC 8594); `info.version=1.0.0`; `API_BASE` frontend + MSW + E2E sincronizados |
| A6e.events | Domain events tipados (ex-A6e.6) | `backend/app/events/` com `Event` base + `register_handler`; zero side-effect inline em use cases | 1 sessão | ✅ 2026-04-22 parcial (ADR-115) — 4 slices mergeados (infra + `AuditLogEvent` + `TaskCreated/UpdatedEvent`); 2 follow-ups abertos |
| A6e.events-migration | Migrar ~14 `audit_log()` inline em routers → `AuditLogEvent` | Padrão estabelecido em A6e.events slice 2 (`CreateFamilyMember` migrado); cada call-site vira emit no use case + handler | 1 sessão | ✅ 2026-04-22 — 10 call-sites (documents 5 + workspaces 4 + invitations 1) emitindo `AuditLogEvent` via `dispatch_sync`; `audit_log`/`audit_service.log` só no `services/` (referência de testes); 1177 backend tests passed |
| A6e.events-followup | Ativar flag `MATHOMS_USE_EVENT_DRIVEN_TASK_NOTIFICATIONS=true` em prod + remover cron | Monitor 48h flag → apagar `scan_and_create_notifications()` polling se zero regressão | 0.3 sessão | ⏸ aguarda janela de prod (pós-F7 deploy) |

**Estimativa total A6e:** 5-7 sessões grandes, ~400+ testes novos.

#### Slice entregue — **FamilyMember aggregate** (branch `a6e/family-member-slice`, 2026-04-20)

| Entrega | Detalhes | Commit |
| --- | --- | --- |
| `FamilyMemberRepository` async | 13 métodos; BankAccount como sub-entidade; cascade delete explícito (SQLite compat); `populate_existing=True` em eager-load | c84af46 |
| DTOs em `schemas/dto/family_member/` | response/command/mapper; mapper recebe vault via Protocol; `convert_global_defaults_to_responses` preserva F6.5E.6 | 2d9074b |
| Refactor `config.py` members/accounts | 5 endpoints delegam ao repo e retornam DTOs; ~130 linhas duplicadas removidas; compat binária via aliases em `schemas/config.py` | 13ece89 |
| Tests + regression gate | 10 unit tests mapper (puros) + 13 repo tests (DB real); BUG-004 sentinela migrada para mapper.py | 4167fa5 |

#### Slice entregue — **Document aggregate** (branch `agent/a6e5-document/*`, 2026-04-21)

| Entrega | Detalhes | Commit |
| --- | --- | --- |
| `DocumentRepository` async | 7 métodos (`list` com filtros, `get_by_id`, `get_by_content_hash`, `find_fuzzy_duplicate_id`, `list_non_error`, `add` flush-opt-out, `delete`); R13 no predicado; não commita (boundary = caller, necessário para savepoint de upload) | `9cbcf2f` |
| DTOs em `schemas/dto/document/` | response (5 DTOs, incluindo `DocumentExtractJsonResponse` e `DocumentReclassifyResponse` que migraram classes inline do router) + command (`DocumentUpdateCommand`) + mapper puro | `16ef59c` |
| Refactor `api/documents.py` | 8 endpoints delegam ao repo; `grep "select(Document" = zero`; upload flow preservado (savepoint + fuzzy-dedupe cross-referencial + cleanup + audit log); compat binária via shim em `schemas/document.py` | `4958d9a` |
| Tests | 15 unit tests mapper (puros, sem DB) + 16 repo tests (DB real; isolamento multi-tenant em todos os métodos; ordenação por `uploaded_at` DESC; fuzzy dedupe cross-tenant safety) | `ab240aa` |
| OpenAPI snapshot | 3 renames (`DocumentUpdateRequest`→`Command`, inline `ExtractJsonResponse`→`DocumentExtractJsonResponse`, inline `ReclassifyResponse`→`DocumentReclassifyResponse`) + descrições populadas | `2c5c134` |

**Impact:** 847 passed / 4 skipped (+31 vs 816 baseline; zero regressão).

**Escopo deixado para frente:** `document_processor.py`, `document_pipeline_sync.py` e `tasks/pipeline_task.py` continuam com ORM direto — migração é R15 (use-case layer) em slice futuro.

#### Slice entregue — **Goal aggregate** (branch `agent/a6e6-goal/*`, 2026-04-21)

| Entrega | Detalhes | Commit |
| --- | --- | --- |
| `GoalRepository` async | 4 métodos para semântica versionada: `get_active_by_type` (vigente), `get_by_id`, `list_by_workspace_and_type` (DESC), `create_new_version` (close active + flush + insert atômico). Validação de `VALID_GOAL_TYPES` em toda op; R13 no predicado; não commita | `41fa878` |
| DTOs em `schemas/dto/goal/` | 4 módulos por tipo (`if_goal.py`, `aporte.py`, `dolar.py`, `alocacao.py`) com 7 DTOs cada + `base.py` (shared response base) + `mapper.py` (`goal_to_typed_response` resolve classe via `GOAL_TYPE_DTO_CLASSES`) | `b2e1f90` |
| Refactor service + router + shim | `goal_service.py` -200 linhas (compute services permanecem puros); `api/goals.py` 16 endpoints com `grep "select(Goal" = zero`; `*UpsertRequest` → `*UpsertCommand`; shim em `schemas/goal.py` preserva compat binária | `eca59b0` |
| Tests | 16 mapper tests (dispatch por tipo, fallbacks de `meta_version`, narrow IF) + 12 repo tests (DB real; `create_new_version` fecha vigente ANTES; cross-tenant safety) | `1c8ecfb` |
| OpenAPI snapshot | 4 renames `*UpsertRequest` → `*UpsertCommand` + docstring descriptions | `8760d7e` |

**Impact:** 884 passed / 4 skipped (+28 vs 856 pós-A6e.5; zero regressão).

**Escopo deixado para frente:** `goal_compute_*.py` são domain logic pura (decisão consciente — não migra); Report lookup (`get_latest_report_patrimonio_liquido`) fica em goal_service até Report virar agregado próprio (slice futuro).

#### Slice entregue — **Task aggregate** (branch `agent/a6e7-task/*`, 2026-04-21)

Último do trilho per-aggregate. 3 sub-agregados: Task + TaskAttachment + TaskSuggestion.

| Entrega | Detalhes | Commit |
| --- | --- | --- |
| 3 repositórios separados | `TaskRepository` (list com filtros + priority_rank CASE S<R<O, list_all, get_by_id/number, list_by_parent subtasks, next_number atômico, add/save/delete); `TaskAttachmentRepository` (só DB — storage fica no service); `TaskSuggestionRepository` (list_by_status default pending, add/save) | `daddb8d` |
| DTOs em `schemas/dto/task/` | 9 módulos especializados: types/response/command/filters/progress/attachment/suggestion/mapper. `*Request` → `*Command`; `TaskProgress` → `TaskProgressResponse` | `93cef55` |
| Refactor services + router + shim | `task_service` + `task_attachment_service` + `task_suggestion_service` delegam aos repos; `api/tasks.py` 17 endpoints com `grep "select(Task\|TaskAttachment\|TaskSuggestion" = zero`; shim em `schemas/task.py` preserva compat binária | `c05e51b` |
| Tests | 18 mapper tests (puros) + 24 repo tests (DB real; filtros, ordenação, isolamento multi-tenant em 3 repos, cross-tenant safety, next_number por workspace) | `0c8fd11` |
| OpenAPI snapshot | 7 renames `*Request`→`*Command` + `TaskProgress`→`TaskProgressResponse` | `042c6ed` |

**Impact:** 926 passed / 4 skipped (+42 vs 884 pós-A6e.6; zero regressão).

**Escopo deixado para frente:** nenhum aggregate residual — per-aggregate track concluído.

---

**Trilho per-aggregate CONCLUÍDO.** Destrava agora **A6e.3** (use cases — application layer R15), **A6e.4** (routers finos ≤50 linhas R16), **A6e.5** (/api/v1/ prefix), **A6e.events** (domain events tipados R17, ex-`A6e.6`) — todas **transversais** a todos os 6 agregados migrados.

**Pré-existente fora de escopo (reportado):** `test_alembic_guardrails::test_offline_sql_generation_works` falha por migration A6b `r6s7t8u9v0w1` usando `batch_alter_table` sem `copy_from`; `test_documents.py` x9 falha por schema drift em `workspaces.use_db_artifacts_override`. Nenhum dos dois tocado pelo slice A6e.1+.2.
