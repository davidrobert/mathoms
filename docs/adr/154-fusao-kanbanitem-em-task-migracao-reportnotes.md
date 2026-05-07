---
id: ADR-154
type: adr
title: "Fusão `KanbanItem` em `Task` + migração `ReportNotes` para `WorkspaceNotes` (Direção E · Onda 1)"
status: Decidido
phase: "Direção E · Onda 1 · M1+M2"
date: "2026-04-29"
relates_to: []
supersedes: ["[[ADR-123]]"]
superseded_by: []
aliases: ["ADR 154"]
tags:
  - area/backend
  - area/multitenancy
  - area/persistence
  - status/decidido
  - type/adr
size_lines: 156
---

# ADR-154 — Fusão `KanbanItem` em `Task` + migração `ReportNotes` para `WorkspaceNotes` (Direção E · Onda 1)

> **M2 sunset entregue (2026-04-29):** tabelas legadas renomeadas para
> `_legacy_kanban_items` / `_legacy_report_notes` (RENAME, dado
> preservado); endpoints `/notes` e `/kanban` retornam HTTP 410 Gone
> com payload informativo. Estratégia conservadora vs DROP direto
> previsto na seção §M2 abaixo: rename é reversível em segundos via
> downgrade; DROP é irreversível sem backup; janela de 7 dias de
> validação não foi cumprida (M1 e M2 no mesmo dia). Drop final
> agendado para PR M3 (sprint+2, ~2026-05-13) após validação. Models
> SQLAlchemy `KanbanItem`/`ReportNotes` permanecem (tablename
> `_legacy_*`) porque `purge_reports.py` ainda faz DELETE em ambos.
> Migration: `a0b1c2d3e4f5_adr154_m2_sunset_legacy.py`. Endpoints:
> `backend/app/api/reports_collab.py` reescrito.

**Status:** Decidido (Direção E · Onda 1 · M1+M2) • **Data:** 2026-04-29 •
**Supersedes** parcial [ADR-123](#adr-123--notas-t6-e-kanban-t3-persistidos-no-backend)
(Kanban e Notas como aggregates separados acoplados ao relatório). Estende
[ADR-074](#adr-074--tasks-como-entidade-de-1ª-classe-fora-do-relatório)
(Task aggregate). Conclui agenda da [ADR-151](#adr-151--remoção-do-modo-tático-do-relatório-direção-e-do-redesign-de-interfaces)
(remoção do Modo Tático).

**Contexto:** Após a remoção do Modo Tático (ADR-151), os aggregates
`KanbanItem` e `ReportNotes` (ADR-123) ficaram órfãos no DB — tabelas
vivas sem consumer no frontend. A análise técnica do data-engineer
durante o brainstorm da Direção E concluiu:

1. **`KanbanItem` é subset degenerado de `Task`** — campos: `titulo`,
   `coluna`, `prioridade`, `prazo`, `categoria`, `essencial`, `ordem`,
   `report_id`. Cada um tem mapeamento direto em `Task`:
   `titulo→title`, `coluna→novo board_column`, `prioridade→novo urgency`,
   `prazo→deadline_date`, `categoria→category`, `essencial→priority`,
   `ordem→novo board_order`, `report_id→novo origin_report_id`. Não há
   campo de Kanban que `Task` não possa absorver.
2. **`ReportNotes` perde semântica fora do relatório** — 1:1 com
   `report_id` via UniqueConstraint, mas o relatório vira "fotografia
   imutável" (ADR-151), e o Kanban T3 acoplado a ele já saiu do produto.
   Manter o aggregate amarrado a `report_id` força a UI a perguntar "de
   qual relatório?" — que já não é a pergunta certa do usuário.
3. **3 aggregates para "coisa pra fazer"** (Decision, Task, KanbanItem)
   geravam confusão; com a fusão sobram 2 modelos ortogonais: `Decision`
   (compromisso) + `Task` (execução).

**Decisão:**

1. **Expandir `Task` (M1, additive)** com 5 colunas nullable:
   - `board_column VARCHAR(32) NULL` — `'a_fazer'|'em_andamento'|'concluido'`. NULL = task fora do board view (default; só itens migrados ou aceitos explicitamente para o board recebem valor).
   - `board_order INTEGER NULL` — preserva ordenação DnD do legado.
   - `origin_report_id VARCHAR(36) NULL FK→reports ON DELETE SET NULL` — rastreia origem documental sem cascatear delete.
   - `urgency VARCHAR(8) NULL` — `'alta'|'media'|'baixa'`, eixo tático ortogonal a `priority` (S/R/O metodológico). Importado de `KanbanItem.prioridade` no backfill; opt-in para tasks novas.
   - `is_board_only BOOLEAN NOT NULL DEFAULT false` — quando `true`, widgets de Tasks (`UpcomingTasksWidget`, listas `/acao` Tarefas) filtram a row fora; evita inflar widgets após backfill de Kanban.
   - `created_from` ganha `'kanban_migration'` no enum.
   - Índice `ix_tasks_ws_board_column` para o board view.

2. **Criar `workspace_notes` (M1)** — multi-row, com `title` opcional,
   `pinned` boolean, `content` text. Substitui `ReportNotes` 1:1 por
   uma tabela workspace-scoped que cobre tanto "anotação livre única"
   quanto "agenda do casal financeira" (múltiplas notas tituladas).
   Índice `ix_workspace_notes_ws_pinned_updated` para a ordenação
   default (pinned desc, updated_at desc).

3. **Backfill via script descartável** (`dev/migrate_kanban_to_task.py`):
   - Cada `KanbanItem` vira uma `Task` com `created_from='kanban_migration'`,
     `is_board_only=true`, `source_suggestion_id=kanban_item.id` (idempotência).
   - `ReportNotes` do workspace concatenam em **uma** `WorkspaceNotes`
     com `title="Notas migradas do relatório"`, `pinned=true`, conteúdo
     formado por `## Relatório <id> — <data>\n<content>` cronológico.
   - Idempotente: re-executar não duplica (skip via
     `source_suggestion_id` para Kanban; via título para Notes).

4. **Endpoints REST adicionados** (`/v1/workspaces/{ws}/notes`): GET,
   POST, PATCH, DELETE. Endpoints legados `/kanban` e `/report_notes`
   permanecem disponíveis até **M2** (sprint+1, em PR separado), depois
   retornam 410 Gone e tabelas são dropadas.

5. **Frontend `<NotasTab/>` real** em `/acao` Notas (substitui
   placeholder ensinante da Onda 6): lista pinned-first, edição inline
   com autosave 500ms + flush onBlur, botão "Nova nota", toggle pin,
   delete. Hook `useWorkspaceNotes(workspaceId)` carrega + expõe CRUD.

6. **Vocabulário de prioridade resolvido**: `Task.priority` (S/R/O)
   continua sendo a classificação **metodológica** (Essencial/
   Recomendada/Opcional, do tarefas.md). `urgency` (alta/media/baixa)
   é o eixo **tático** importado do Kanban — opt-in. UI default mostra
   priority; tasks com urgency podem expor um chip secundário.

7. **Board view em `/acao` Tarefas: deferred (não-v1)**. M1 entrega só
   a fundação (DB + endpoints + backfill + Notas UI). DnD / Kanban view
   real em `/acao` é roadmap separado — itens migrados aparecem na lista
   normal de Tasks (quando `is_board_only=false`) ou em board view
   futuro (quando `true`).

**Consequências:**

- ✅ Modelo de domínio limpo: 2 aggregates ortogonais (`Decision` +
  `Task`) cobrem todo o ritual sugestão→decisão→execução.
- ✅ `WorkspaceNotes` desacoplado do relatório — usuário pode anotar
  contexto que não cabe em Decision/Task sem precisar escolher um
  report-id que já não importa.
- ✅ Migration M1 zero-downtime (todas as colunas nullable; tabela
  nova vazia). Backfill idempotente roda em segundos por workspace
  (volume baixo: dezenas de itens).
- ✅ Tasks migradas de Kanban marcadas com `is_board_only=true`
  evitam poluir `UpcomingTasksWidget` e listas de Tarefas — a fusão é
  invisível para quem nunca usou o Kanban.
- ⚠️ Tabelas `kanban_items` e `report_notes` permanecem no DB até M2
  (sprint+1). Endpoints REST continuam disponíveis no intervalo, mas
  sem consumer no frontend. Aceitável: PR menor, validação 7+ dias em
  prod antes do drop.
- ⚠️ `urgency` é nullable e opt-in — sem UI inicial para editar (só
  herda de Kanban migrado). Se produto pedir, futura Onda adiciona
  toggle no `TaskFormDialog`.
- ❌ Quem usava o Kanban T3 do Modo Tático perde a coluna visual no
  curto prazo (já tinha perdido na ADR-151; M1 só completa a migração
  silenciosa para Tasks). Board view real é roadmap separado.

**Migration M1 → M2 → M3 (revisada 2026-04-29):**

- M1 ✅ (entregue 2026-04-29): tabelas/colunas adicionadas + backfill
  + endpoints + UI de Notas. **Tabelas legadas vivas, sem consumer
  no frontend.**
- M2 ✅ (entregue 2026-04-29): RENAME `kanban_items` →
  `_legacy_kanban_items` + RENAME `report_notes` →
  `_legacy_report_notes` (estratégia conservadora vs DROP direto
  porque mesmo-dia da M1 não cumpriu janela de 7 dias). Endpoints
  `/notes` e `/kanban` retornam HTTP 410 Gone com payload informativo
  apontando para os novos endpoints (`/workspaces/{ws}/notes` e
  `/workspaces/{ws}/tasks`). Frontend `lib/api/reports.ts` ganha
  `@deprecated` JSDoc. Models permanecem apontando para `_legacy_*`
  porque `purge_reports.py` ainda faz DELETE em ambos.
- M3 (próximo PR, sprint+2 após validação ≥7 dias): `DROP TABLE
  _legacy_kanban_items`, `DROP TABLE _legacy_report_notes`, remover
  models `KanbanItem`/`ReportNotes`, remover `_delete_report_collab`
  de `purge_reports.py`, deletar funções legadas em
  `lib/api/reports.ts`. PR pequeno, baixo risco.

**Referências de código:**

- `backend/alembic/versions/f0a1b2c3d4e5_adr154_kanban_to_task_workspace_notes.py` — migration M1.
- `backend/app/models/task.py` — colunas + enums novos.
- `backend/app/models/workspace_note.py` — aggregate novo.
- `backend/app/repositories/workspace_notes_repository.py`,
  `backend/app/application/workspace_notes/` (5 use cases),
  `backend/app/schemas/dto/workspace_note/`,
  `backend/app/api/workspace_notes.py`.
- `dev/migrate_kanban_to_task.py` — backfill idempotente.
- `frontend/src/lib/api/workspace-notes.ts` — cliente HTTP.
- `frontend/src/hooks/useWorkspaceNotes.ts` — hook CRUD.
- `frontend/src/app/(app)/acao/_components/NotasTab.tsx` — UI real.
- Tests:
  `backend/tests/test_workspace_notes_api.py` (8),
  `backend/tests/test_kanban_to_task_backfill.py` (6 paridade),
  `frontend/tests/hooks/useWorkspaceNotes.test.tsx` (6),
  `frontend/tests/components/NotasTab.test.tsx` (3).
