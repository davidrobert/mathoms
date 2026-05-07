---
id: TRACK-onda-1-kanban-task-migration
type: track
title: "Track — Onda 1: Migration `kanban_items` + `report_notes` → `tasks` + `workspace_notes`"
sprint: A11
status: consumed
created_at: null
consumed_at: null
agent_role: null
tags:
  - type/track
  - sprint/a11
  - status/consumed
---

# Track — Onda 1: Migration `kanban_items` + `report_notes` → `tasks` + `workspace_notes`

> **Status:** ✅ Entregue (M1) em 2026-04-29 (commits `6b21207`/`c8f0ed4`/
> `4529192`/`0f9b5a3`/`77ce046`/`8adaf60` em `main`,
> [ADR-154](../DECISIONS.md#adr-154--fusão-kanbanitem-em-task--migração-reportnotes-para-workspacenotes-direção-e--onda-1),
> [PR #20](https://github.com/davidrobert/mathoms/pull/20)). Mantido em
> `docs/agent_prompts/` como referência histórica. M2 (drop `kanban_items`
> + `report_notes` + endpoints 410 Gone) fica para sprint+1, em PR
> separado, após validação 7+ dias em workspace Allen.
>
> **Contexto:** Este prompt é self-contained para nova sessão Claude
> Code dedicada à Onda 1 da Direção E. Branch sugerida:
> `agent/onda-1-kanban-task-migration/<ts>`, partindo de `origin/main`
> **após o merge das Ondas 2/3/4/6** (PR atual:
> https://github.com/davidrobert/mathoms/pull/18).
>
> **Pode rodar em paralelo com a Onda 5** (`track_onda_5_suggestion_aggregate.md`)
> em branch separada. Conflitos esperados: trivial em CHANGELOG.md +
> sequência `down_revision` Alembic (resolver com `alembic merge`).

---

## Briefing

Fundir o aggregate **`KanbanItem`** (ADR-123) no aggregate **`Task`**
(ADR-074) e migrar **`ReportNotes`** (ADR-123) para **`WorkspaceNotes`**
(novo, workspace-scoped). Implementar tab Notas em `/acao` consumindo
o novo aggregate.

Validação técnica feita pelo [data-engineer](.claude/agents/data-engineer.md)
durante o brainstorm (sumarizado em `~/.claude/plans/quero-repensar-as-interfaces-mellow-nova.md`):

> KanbanItem é **subset degenerado** de Task + 2 campos próprios
> (`report_id`, `ordem`). Não há campo de Kanban que Task não consiga
> absorver. Tecnicamente trivial fundir.

`report_notes` (1:1 com report) faz menos sentido após a remoção do
Modo Tático (ADR-151) — perde-se a semântica do `report_id`. Migração
para `workspace_notes` (texto livre por workspace) **desacopla do
relatório que está sendo desmontado** (recomendação do data-engineer).

## Estado atual da Direção E (pré-Onda 1)

Ondas já entregues (assumir mergeadas em `main`):

- Ondas 2/3/4/6 — ver detalhes em
  `docs/agent_prompts/track_onda_5_suggestion_aggregate.md` §Estado.
- Tab Notas em `/acao` (Onda 6) tem **placeholder ensinante**
  aguardando esta Onda 1.
- Tabelas `kanban_items` e `report_notes` permanecem no DB **sem
  consumer no frontend** desde a remoção do Modo Tático (ADR-151).
  Endpoints REST permanecem disponíveis mas órfãos.

Onda paralela (não bloqueia):
- **Onda 5** (Suggestion full-stack) — branch separada. Conflitos
  triviais a resolver no merge.

## Schema unificado proposto (ratificar com data-engineer)

### Mudanças em `tasks`

```sql
ALTER TABLE tasks
  ADD COLUMN board_column VARCHAR(32) NULL,    -- 'a_fazer'|'em_andamento'|'concluido'
  ADD COLUMN board_order  INTEGER     NULL,    -- ordem dentro da coluna (DnD)
  ADD COLUMN origin_report_id VARCHAR(36) NULL, -- rastreio (não escopo) ↗ reports.id
  ADD CONSTRAINT fk_tasks_origin_report FOREIGN KEY (origin_report_id)
    REFERENCES reports(id) ON DELETE SET NULL;

CREATE INDEX CONCURRENTLY ix_tasks_ws_board_column
  ON tasks (workspace_id, board_column);
```

`board_column` mapeia 1-to-1 do antigo `KanbanItem.coluna`. Pode ser
**coluna gerada (computed)** a partir de `status`:

| Task.status | board_column |
|---|---|
| `pending`, `blocked` | `a_fazer` |
| `in_progress` | `em_andamento` |
| `done` | `concluido` |
| `cancelled` | `concluido` (ou `null` para ocultar) |

**Decisão pendente** (data-engineer + product-designer):
- (a) `board_column` é **column física** (nullable) — só preenchida em
  itens originados do Kanban; ou
- (b) `board_column` é **computed** sempre derivada de `status`?

Recomendação minha: **(a)**. Razão: a maioria das Tasks **não** são de
Kanban e não devem aparecer no board view (filtrar `WHERE board_column
IS NOT NULL`). Tarefas migradas do Kanban ficam com `board_column`
preenchido; futuras Tasks só preenchem se o usuário arrastar para o
board view.

### Vocabulário de prioridade (decisão de UX!)

Conflito real:
- `Task.priority` (S/R/O) — mapeia metodologia (Saúde/Reserva/Outro?
  Strategic/Routine/Optional? Confirmar enum semantics)
- `KanbanItem.prioridade` (alta/media/baixa) — urgência tática

**São eixos distintos ou redundantes?** Designer apontou que isso
é decisão de UX, não de DB. **Convocar product-designer no início
desta sessão para travar.** Recomendação minha:

- Manter `priority` (S/R/O) como **classificação metodológica**
  (existente)
- Adicionar `urgency VARCHAR(8) NULL` (alta/media/baixa) **só
  preenchido em itens migrados do Kanban**, ou opt-in para usuário
  que quiser eixo de urgência separado

### Nova tabela `workspace_notes`

```sql
CREATE TABLE workspace_notes (
  id           VARCHAR(36) PRIMARY KEY,
  workspace_id VARCHAR(36) NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  content      TEXT NOT NULL DEFAULT '',
  updated_at   TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
  -- 1 row por workspace (UNIQUE constraint)
  UNIQUE (workspace_id)
);

CREATE INDEX ix_workspace_notes_ws ON workspace_notes (workspace_id);
```

Ou multi-row (se quiser múltiplas notas):
```sql
-- alternativa: várias notas por workspace
CREATE TABLE workspace_notes (
  id           VARCHAR(36) PRIMARY KEY,
  workspace_id VARCHAR(36) NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  title        VARCHAR(200) NULL,
  content      TEXT NOT NULL DEFAULT '',
  pinned       BOOLEAN NOT NULL DEFAULT false,
  created_at   TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
  updated_at   TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);
```

**Decisão pendente:** 1 nota textão livre (single textarea) ou
múltiplas com título? Designer não ressaltou; minha recomendação:
**multi-nota com title + pinned**. Cobre tanto "anotação livre" quanto
"agenda do casal financeira" sem custo extra.

## Migration em 2 fases (ADR-090 disciplina)

**M1 — additive (zero-downtime, M-day):**

1. ALTER TABLE tasks (campos novos, todos nullable) com `CONCURRENTLY`
2. CREATE TABLE workspace_notes
3. **Backfill idempotente** (script Python fora da migration):
   - Para cada `kanban_item`, INSERT em `tasks` com:
     - `created_from='kanban_migration'`
     - `number=MAX(number)+1` (lock na linha de workspaces?)
     - mapping `coluna→status` + `coluna→board_column`
     - `origin_report_id=report_id`
     - `priority='O'` (default Optional) + `urgency` derivado de
       `prioridade`
   - Para cada workspace com pelo menos um `report_notes` row,
     concatenar conteúdos por `report_id` cronológico em uma
     `workspace_notes` row (com title="Notas migradas do relatório")
4. Tags `is_board_only` (ou similar) para itens migrados — facilita
   filtragem em `UpcomingTasksWidget` (não mostra itens de Kanban
   migrado para não inflar widget de tarefas próximas)
5. Validação pós-backfill: count `kanban_items` == count `tasks WHERE
   created_from='kanban_migration'`

**M2 — drop (sprint+1, M+7-dias-mín):**

1. Frontend já usa hooks novos exclusivamente
2. Endpoints `/kanban` e `/report_notes` deprecated (retornam 410 Gone)
3. DROP TABLE kanban_items
4. DROP TABLE report_notes
5. (Opcional) RENAME para `_legacy_kanban_items` antes de drop, com
   drop em M+30 dias para safety

**Janela de manutenção:** hot. Volume é baixo (centenas de itens por
workspace). Backfill roda em minutos.

## Endpoints REST a adicionar/modificar

```
# Tasks (additive)
GET /v1/workspaces/{ws}/tasks?view=board        # filtra board_column NOT NULL
GET /v1/workspaces/{ws}/tasks?view=list         # default (board_column ignored)

# Workspace notes
GET    /v1/workspaces/{ws}/notes                # lista todas
POST   /v1/workspaces/{ws}/notes                # cria nova
PATCH  /v1/workspaces/{ws}/notes/{id}           # update content/title/pinned
DELETE /v1/workspaces/{ws}/notes/{id}

# Kanban (deprecate)
# GET /v1/workspaces/{ws}/reports/{rid}/kanban  → 410 Gone após M2

# Report notes (deprecate)
# GET /v1/workspaces/{ws}/reports/{rid}/notes   → 410 Gone após M2
```

OpenAPI snapshot (ADR-109): `make update-openapi-snapshot` obrigatório.

## Frontend — componentes a criar/modificar

### `<NotasTab/>` em `/acao` (substituir placeholder)

- Localização atual: `frontend/src/app/(app)/acao/_components/NotasTab.tsx`
  (placeholder ensinante)
- Substituir empty state pela UI real:
  - Lista de notas (cards) ordenadas por `pinned desc, updated_at desc`
  - Card editável inline (clicar pra expandir editor; autosave 500ms)
  - Botão "+ Nova nota"
  - Toggle pin/unpin
- Hook novo: `useWorkspaceNotes(workspaceId)`

### Board view em `/acao` Tarefas (opcional v1)

- Toggle no `TasksHeader` (atual `ViewToggle` tem 3 views: priority,
  deadline, category — adicionar 4ª: `board`)
- Quando ativo, render Kanban de 3 colunas com `<TaskCard/>` agrupado
  por `board_column`
- DnD com `@dnd-kit/core` (já em deps) atualiza `board_column` +
  `board_order`

**Decisão pendente:** v1 inclui board view ou só faz a fundação
(migration + endpoints) e deixa board view para onda futura?
Recomendação: **só fundação em v1**. Itens migrados do Kanban
aparecem na lista normal de Tarefas; usuário acessa pelo `view=list`
default. Board view é v2.

### Hooks

- `useWorkspaceNotes` — CRUD + autosave debounce
- `useTasks` aceita opcional `view: 'list' | 'board'` (atualmente só
  list)
- Remover (após M2): hooks/refs que importam `kanban_items` ou
  `report_notes` (não há nenhum no frontend pós Ondas 2/3/4/6, então
  nada a remover ali)

## Critérios de aceite

- [ ] Nova ADR (ADR-153 ou ADR-154 dependendo da Onda 5) "Fusão
  KanbanItem em Task + migração ReportNotes para WorkspaceNotes"
  superseded ADR-074 e ADR-123
- [ ] Migration M1 (additive) entregue + backfill idempotente
- [ ] Migration M2 (drop) **agendada** mas não executada (rodar em
  sprint+1 após validação)
- [ ] Endpoint `GET /tasks?view=board` (param novo)
- [ ] Endpoints CRUD `/notes` (workspace-scoped)
- [ ] OpenAPI snapshot atualizado
- [ ] `<NotasTab/>` real (lista + editor inline com autosave)
- [ ] `useWorkspaceNotes` hook
- [ ] Tests: paridade backfill (`tests/test_kanban_to_task_backfill.py`),
  unit hooks, E2E `@critical` (criar/editar/deletar nota)
- [ ] CHANGELOG entry
- [ ] Pre-commit verde · code-style baseline mantido
- [ ] Validação manual em workspace Allen: Kanban items aparecem em
  /acao Tarefas com `created_from='kanban_migration'`; notas migradas
  aparecem em /acao Notas

## Fluxo de execução sugerido

1. **Phase 1 — Travar decisões pendentes (Plan mode):**
   - Convocar [product-designer](.claude/agents/product-designer.md)
     para vocabulário de prioridade Task (S/R/O vs urgency)
   - Convocar [data-engineer](.claude/agents/data-engineer.md) para
     ratificar schema (board_column física vs computed; workspace_notes
     single-row vs multi-row)
   - Escrever nova ADR superseder ADR-074 + ADR-123 (parcial)

2. **Phase 2 — Backend M1 (1.5 dias):**
   - Migration Alembic additive
   - Backfill script idempotente em `dev/migrate_kanban_to_task.py`
     (modelo: `dev/migrate_decisions_to_db.py`)
   - Modelo SQLAlchemy expandido (Task + WorkspaceNotes)
   - Repository + use cases
   - Endpoints + DTOs + OpenAPI snapshot
   - Tests unit + integração + paridade backfill

3. **Phase 3 — Frontend (1 dia):**
   - Hook `useWorkspaceNotes`
   - `<NotasTab/>` real (substituir placeholder)
   - Tests vitest + E2E

4. **Phase 4 — Docs + commit + push:**
   - ADR + CHANGELOG
   - Smoke test humano em Allen
   - PR

5. **Phase 5 (sprint+1) — M2 drop:**
   - Validar 7+ dias de uso real sem regressão
   - Migration drop em commit separado
   - Remover endpoints deprecated

## Pontos críticos / riscos

1. **Vocabulário de prioridade não-resolvido** vira backfill
   irreversível ruim. Mitigação: travar **antes** da M1 com
   product-designer.
2. **`number` único por workspace** — conflito de lock se backfill
   concorre com criação manual. Mitigação: rodar backfill em janela
   curta (poucos minutos) ou usar `MAX(number)+ROW_NUMBER()` em
   transação única.
3. **`UpcomingTasksWidget` ruído** — itens de Kanban migrados podem
   inflar widget. Mitigação: filtrar por `board_column IS NULL` ou
   flag `is_board_only` no widget.
4. **`report_id` em KanbanItem perde âncora** — itens originados de
   relatórios deletados ficam órfãos. Mitigação: `origin_report_id
   ON DELETE SET NULL` (não cascateia delete).

## Arquivos relevantes (referência rápida)

**Já entregues nas Ondas 2-6:**
- `frontend/src/app/(app)/acao/_components/NotasTab.tsx` (placeholder
  — Onda 1 substitui empty state)
- `backend/app/models/task.py` (Task aggregate existente — Onda 1
  expande)
- `backend/app/models/report_collab.py` (KanbanItem + ReportNotes —
  Onda 1 deprecates)

**ADRs a ler:**
- ADR-074 (Task aggregate)
- ADR-123 (KanbanItem + ReportNotes — superseded por esta onda)
- ADR-090 (Money sempre Decimal/Money/cents — relevante se Tasks
  ganham campo monetário)
- ADR-109 (OpenAPI snapshot)
- ADR-151 (remoção do Modo Tático — fundamenta a remoção do
  KanbanItem/ReportNotes)
- ADR-152 (rota `/acao` com tabs — fundamenta onde Notas vive)

## Não fazer nesta sessão

- ❌ M2 drop (deixar para sprint+1 após validação em prod)
- ❌ Board view em `/acao` Tarefas (v1 só fundação; board view futura)
- ❌ DnD para Kanban (futuro)
- ❌ LLM-based note suggestions (futuro)
- ❌ Mexer em Decisions (Onda 5 que mexe)

## Smoke test humano antes do PR

1. Abrir `/acao?tab=notas` em workspace Allen — confirmar que notas
   migradas de `report_notes` aparecem
2. Criar nova nota → editar → autosave → reload → confirmar persistido
3. Pin/unpin → reload → confirmar ordem correta
4. Abrir `/acao?tab=tarefas` — confirmar que Kanban items migrados
   aparecem com flag identificável (ou comportamento esperado)
5. Confirmar que `UpcomingTasksWidget` não inflou (filtrado)

## Branch + commits

- Partir de `origin/main` pós-merge das Ondas 2/3/4/6 (PR #18)
- Branch: `agent/onda-1-kanban-task-migration/<yyyyMMdd-HHmm>`
- Commits sugeridos:
  1. `feat(db): tasks board_column + workspace_notes (M1, ADR-XXX)`
  2. `feat(api): /tasks?view=board + /notes endpoints`
  3. `feat(frontend): NotasTab real + useWorkspaceNotes`
  4. `chore(migration): backfill kanban_items → tasks + report_notes
     → workspace_notes`
  5. `docs(adr): ADR-XXX + CHANGELOG`
- PR único.
- M2 (drop) em PR separado em sprint+1.

## Coordenação com Onda 5 (paralela)

Conflitos previstos a resolver no merge sequencial:

- `docs/CHANGELOG.md` — ambas adicionam entry em `[Unreleased]`.
  Resolver mantendo ambos.
- `backend/alembic/versions/` — ambas criam migrations. Quem mergear
  segundo precisa rebase: ajustar `down_revision` para apontar para
  o head atual de main (que já incluiu a primeira migration).
- `backend/app/models/__init__.py` — ambas registram modelos novos.
  Resolver mantendo ambos imports.
- `backend/app/api/__init__.py` — ambas adicionam routers. Resolver
  mantendo ambos.

Sem sobreposição em:
- Frontend (Onda 5 mexe Inbox + SuggestionsBanner; Onda 1 mexe Notas)
- Pipeline (Onda 5 toca E5; Onda 1 não toca)
- Tabelas (suggestions vs tasks/workspace_notes — separadas)

**Recomendação operacional:** se ambas paralelas, mergear Onda 1
primeiro (menor) e Onda 5 depois (maior). Onda 5 pode usar Tasks
expandido (board_column) se quiser criar tasks vinculadas com origem
em board, mas em v1 não precisa.
