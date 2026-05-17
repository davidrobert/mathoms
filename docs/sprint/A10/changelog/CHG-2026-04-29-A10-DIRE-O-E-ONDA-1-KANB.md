---
id: CHG-2026-04-29-A10-DIRE-O-E-ONDA-1-KANB
type: changelog-entry
date: "2026-04-29"
sprint: A10
adrs: ["[[ADR-074]]", "[[ADR-123]]", "[[ADR-136]]", "[[ADR-153]]", "[[ADR-154]]"]
commits: ["e9f0a1b2c3d4"]
summary: |
  Direção E — Onda 1: `KanbanItem` → `Task` + `ReportNotes` → `WorkspaceNotes` (M1, 2026-04-29). - **Direção E — Onda 1: `KanbanItem` → `Task` + `ReportNotes` → `WorkspaceNotes` (M1, 2026-04-29):** Onda 1 da Direção E entregue como migration **M1 additive**
tags:
  - type/changelog-entry
  - sprint/a10
---


# Direção E — Onda 1: `KanbanItem` → `Task` + `ReportNotes` → `WorkspaceNotes` (M1, 2026-04-29)

- **Direção E — Onda 1: `KanbanItem` → `Task` + `ReportNotes` → `WorkspaceNotes` (M1, 2026-04-29):**

  Onda 1 da Direção E entregue como migration **M1 additive**
  ([ADR-154](../../../DECISIONS.md#adr-154--fusão-kanbanitem-em-task--migração-reportnotes-para-workspacenotes-direção-e--onda-1)).
  Funde o aggregate `KanbanItem` (ADR-123) no aggregate `Task`
  (ADR-074) e migra `ReportNotes` (ADR-123) para um aggregate novo
  `WorkspaceNotes` (workspace-scoped, multi-row, com pin). Substitui
  o placeholder ensinante de Notas em `/acao` (Onda 6) por UI real.

  **Backend:**
  - Migration Alembic `e9f0a1b2c3d4`: ALTER `tasks` ADD `board_column`,
    `board_order`, `urgency`, `origin_report_id` (FK→reports SET NULL),
    `is_board_only`. CREATE TABLE `workspace_notes`. Índice
    `ix_tasks_ws_board_column`. `created_from` ganha `'kanban_migration'`.
    Zero-downtime; offline SQL preview validado pelo
    `test_alembic_guardrails`.
  - Aggregate `WorkspaceNotes` completo (model, repository, 4 use
    cases, DTOs, mapper) seguindo padrão Decision (ADR-136).
  - 4 endpoints REST `/v1/workspaces/{ws}/notes` (GET list, POST,
    PATCH, DELETE 204) registrados em `main.py` e refletidos no
    OpenAPI snapshot.
  - Backfill idempotente em `dev/migrate_kanban_to_task.py`: cada
    `KanbanItem` vira `Task` com `created_from='kanban_migration'`,
    `is_board_only=true`, `source_suggestion_id=kanban_item.id`;
    `report_notes` do workspace concatenam em **uma** `WorkspaceNotes`
    com `title="Notas migradas do relatório"`, `pinned=true`. Re-run
    skipa via `source_suggestion_id` / título.
  - Tests: 8 endpoint integration + 6 backfill paridade
    (`test_workspace_notes_api.py`, `test_kanban_to_task_backfill.py`),
    todos verdes.

  **Frontend:**
  - `frontend/src/lib/api/workspace-notes.ts` (cliente HTTP) +
    `frontend/src/hooks/useWorkspaceNotes.ts` (CRUD + reload).
  - `<NotasTab/>` real em `/acao` (Onda 6 placeholder substituído):
    lista pinned-first, edição inline com autosave 500ms (flush
    onBlur), botão "Nova nota", toggle pin, delete inline.
  - Tests vitest: 6 hook + 3 component (todos verdes).

  **Decisões de UX/schema travadas:**
  - `board_column` é coluna **física nullable** (não computada de
    `status`) — só preenchida em itens de origem Kanban; board view
    futuro filtra `WHERE board_column IS NOT NULL`.
  - `priority` (S/R/O metodológico) e `urgency` (alta/media/baixa
    tático) são **eixos ortogonais** — UI default mostra priority;
    urgency é opt-in (herdado do Kanban migrado).
  - `workspace_notes` é **multi-row** com `title` opcional + `pinned`;
    cobre tanto "anotação livre única" quanto "agenda do casal"
    (múltiplas notas tituladas).
  - **Board view em `/acao` Tarefas: deferred** (não-v1). M1 entrega
    fundação; itens migrados aparecem em listas normais (filtrados
    por `is_board_only` em widgets como `UpcomingTasksWidget`).

  **M2 (sprint+1, em PR separado):** drop tabelas legadas
  `kanban_items` + `report_notes`, endpoints `/kanban` e
  `/report_notes` retornam 410 Gone. Roda só após validação manual
  em workspace Allen + 7 dias sem regressão.

- **Direção E — Onda 5: aggregate `Suggestion` full-stack
  ([ADR-153](../../../DECISIONS.md#adr-153--suggestion-aggregate-direção-e--onda-5-proposal-imutável--state-machine-simples),
  2026-04-29):** Peça central da Direção E — completa o ritual
  *relatório → sugere → usuário aceita/modifica/descarta em `/acao`
  → vira Decision*.

  **Backend:** modelo `Suggestion` (proposal imutável + state machine
  simples Pendente/Aceita/Modificada/Descartada), migration Alembic,
  repositório, 8 use cases (list, count, get, accept, modify, dismiss,
  regenerate-for-report) + protocols, router REST com 7 endpoints.
  Aceitar cria `Decision` via use case canônico (ADR-136), com evento
  extra `derivation` para rastreabilidade. OpenAPI snapshot atualizado.

  **Pipeline:** `pipeline/domain/services/suggestion_generator.py` —
  gerador determinístico puro com 5 regras canônicas (TRS desalinhada,
  reserva insuficiente, alocação fora do alvo, aporte abaixo da meta,
  dolarização atrasada). Cap=6, ranking severity → amount, dedup_key
  com buckets que toleram ruído pequeno. `SuggestionDraft` em
  `pipeline/domain/types/suggestion.py` preserva boundary do pipeline
  (não importa backend). Trigger via endpoint dedicado, NÃO hook do
  pipeline (idempotência + boundary respeitado).

  **Frontend:** cliente `lib/api/suggestions.ts`, hook `useSuggestions`,
  `useSuggestionsCount` real (substitui stub Onda 4). `SuggestionCard`
  em `acao/_components/` com Aceitar/Modificar/Descartar via dialogs
  locais; `InboxTab` agora lista cards filtráveis. `SuggestionCallout`
  inline em S2/S7 + agregador "Próximos passos" no fim do relatório.
  Severidade tripla (info/warning/danger) com faixa lateral 3px +
  ícone Lucide + copy de leigo escondendo vocabulário event-sourced.

  **Testes:** 40 backend (10 use case + 10 API + 20 unit gen) + 11
  frontend (6 hook + 5 helper); suítes completas verdes (688 vitest +
  24 alembic guardrails).
