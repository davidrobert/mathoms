---
id: ADR-072
type: adr
title: "Multi-tenancy: `workspace_id` scoping explícito + `WorkspaceMember` para multi-família"
status: Decidido
phase: "F8"
date: "2026-04-15"
relates_to: []
supersedes: []
superseded_by: []
aliases: ["ADR 072"]
tags:
  - type/adr
  - status/decidido
size_lines: 48
---

# ADR-072 — Multi-tenancy: `workspace_id` scoping explícito + `WorkspaceMember` para multi-família

**Status:** Decidido (F8) • **Data:** 2026-04-15 • **Contexto da task:** F8.0 — Fundação Goals & Tasks

**Contexto:** Até F6.5 o produto operou assumindo **1 workspace por usuário** (query `Workspace WHERE owner_id = user.id` replicada em helpers `_get_workspace(user)` em cada arquivo de API — ex: [backend/app/api/documents.py:30](backend/app/api/documents.py:30)). Esse contrato foi aceitável no MVP com o workspace inicial de dogfood como único tenant. Para F8, a premissa do produto muda: **"será utilizado por diferentes clientes (e famílias) com objetivos, metas e dinâmicas próprias e distintas"**. Isso exige:

1. Múltiplos workspaces por usuário (um consultor pode acompanhar várias famílias).
2. Múltiplos usuários por workspace (cônjuges, dependentes, contador convidado).
3. Isolamento rigoroso: zero vazamento cross-tenant em queries, notificações, LLM prompts, exports.

**Alternativas consideradas:**
- (A) **Postgres Row-Level Security (RLS)** — `CREATE POLICY ... USING (workspace_id = current_setting('app.workspace_id')::uuid)`. Segurança no banco, independente da aplicação.
  - ❌ Rejeitada por ora: dual-db SQLite (dev) + PostgreSQL (prod) do [ADR-039](#adr-039--dual-db-sqlite-dev--postgresql-prod) — SQLite não tem RLS. Forçaria divergência dev/prod ou migração para só-PG no dev.
- (B) **Scoping explícito no service layer + lint custom** — toda query recebe `workspace_id` como primeiro argumento; ruff custom rule barra queries sem filtro.
  - ✅ **Escolhida**: portável entre SQLite e Postgres, testável, e o lint evita regressão humana.
- (C) **Continuar com `owner_id` implícito** — manter 1:1 user↔workspace e resolver multi-família via múltiplos users.
  - ❌ Rejeitada: quebra o caso do consultor com várias famílias e não acomoda múltiplos membros adultos com login próprio.

**Decisão:**
1. **Modelo `WorkspaceMember`** (nova tabela) — `(workspace_id, user_id, role, invited_by, joined_at)`. Roles iniciais: `owner`, `member`. Substitui o uso exclusivo de `Workspace.owner_id` (que permanece como "criador original" por audit, mas não é mais usado como filtro de acesso).
2. **Resolução explícita via path param** — todo endpoint novo de F8+ usa prefixo `/api/workspaces/{workspace_id}/...`. A dependency FastAPI `get_current_workspace()` valida que o `user_id` tem `WorkspaceMember` na `workspace_id` pedida; 403 se não tiver.
3. **Lint rule custom** — `scripts/lint/check_workspace_scoping.py` (CI-gated) escaneia `backend/app/services/**/*.py` por queries (`select(X).where(...)`, `db.execute(...)`) e falha se a primeira condição não referenciar `workspace_id`. Exceções marcadas com `# tenancy: global` (ex: `User` auth, `Category` templates globais).
4. **Services recebem `workspace_id` como primeiro argumento**, nunca inferem por `user_id`. Padrão obrigatório para qualquer código novo: `def list_tasks(workspace_id: UUID, filters: TaskFilters) -> list[Task]`.
5. **Testes de isolamento automáticos** — factory cria 2 workspaces, e para cada novo endpoint há teste `test_<endpoint>_tenant_isolation` que verifica que dados do WS-A nunca vazam em resposta com token do WS-B.
6. **Migração dos endpoints legados** — endpoints pré-F8 continuam usando `_get_workspace(user)` até serem tocados. Quando forem tocados, migram para `get_current_workspace()`. Deadline rígido: F8.4 (cutover final).
7. **UUIDs não-enumeráveis** — todas as novas tabelas usam `uuid.uuid4()` (já é padrão; reforçar nos novos models).

**Consequências:**
- ✅ Multi-família viável sem mudar banco (SQLite dev + Postgres prod continua valendo)
- ✅ Path-based workspace resolution é explícito, debugável, e funciona bem com OpenAPI/typed clients no frontend
- ✅ Lint custom pega regressões antes do review humano
- ✅ `WorkspaceMember` abre caminho para RBAC granular futuro sem re-modelagem (roles evoluem)
- ⚠️ Migração dos 10+ endpoints legados é esforço incremental, não big-bang — aceito
- ⚠️ Sem RLS, bug na app = vazamento. Mitigado por lint + testes de isolamento + audit log
- ❌ Cross-workspace queries (ex: "advisor dashboard agregado") exigem endpoint especial com check explícito por workspace — aceito como débito documentado

**Implementação inicial (F8.0):**
- Migration alembic: criar tabela `workspace_members`; backfill `(workspace_id, owner_id, 'owner', NULL, created_at)` para todo `Workspace` existente.
- `backend/app/core/tenancy.py` com `get_current_workspace(workspace_id: UUID, user = Depends(get_current_user), db = Depends(get_db))`.
- `scripts/lint/check_workspace_scoping.py` + job `tenancy-lint` no CI.
- Documentação em `docs/reference/tenancy.md` (criar) com exemplos de do/don't.

**Débito explícito (fora do escopo desta ADR):**
- RBAC granular por papel (`read_only`, `approver`, `admin`) — endereçar quando primeiro consultor pedir.
- Workspace sharing UI (convite, aceite, revogação) — F9+.
- Cross-tenant analytics (produto) — requer ADR própria quando surgir.
