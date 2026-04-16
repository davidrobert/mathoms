# Multi-tenancy — Guia prático

> **Referências normativas:**
> - [ADR-072](DECISIONS.md#adr-072--multi-tenancy-workspace_id-scoping-explícito--workspacemember-para-multi-família) — tenancy original (F8)
> - [ADR-078](DECISIONS.md#adr-078--workspace-sharing-convites-viewer-role-forced-logout) — workspace sharing (F9)
>
> Este documento traduz as ADRs em padrões de código e checklist de revisão.

---

## TL;DR

1. Todo endpoint novo usa prefixo `/api/workspaces/{workspace_id}/...`.
2. Todo endpoint novo depende de `get_current_workspace` (não de `get_current_user` + resolução implícita).
3. Todo service recebe `workspace_id` como **primeiro argumento**.
4. Toda query SQLAlchemy em service/API inclui `Model.workspace_id == workspace_id` em algum `.where(...)` da expressão.
5. CI bloqueia merges que violem a regra 4 via `tenancy-lint`.

---

## 1. Arquitetura

### Entidades envolvidas

| Entidade | Papel |
|---|---|
| [`User`](../backend/app/models/user.py) | Identidade do humano que faz login. Pode pertencer a múltiplos workspaces. Tem `token_version` para invalidação de sessão (F9). |
| [`Workspace`](../backend/app/models/workspace.py) | Unidade de tenancy. Uma família, um cliente consultor, um CTF de teste. |
| [`WorkspaceMember`](../backend/app/models/workspace_member.py) | Relação N:N com `role`. Determina **acesso e nível de permissão**. |
| [`WorkspaceInvitation`](../backend/app/models/workspace_invitation.py) | Convite pendente (F9). Token hash + TTL 72h + uso único. |
| [`AuditLog`](../backend/app/models/audit_log.py) | Registro imutável de ações sensíveis. Reusado por F9 para eventos de membership. |

### Diferença entre `owner_id` e `WorkspaceMember`

- `Workspace.owner_id` = **criador original** do workspace (imutável, usado para audit).
- `WorkspaceMember.user_id + role` = **permissão de acesso atual**.

A partir de F8.0, toda autorização passa por `WorkspaceMember`. Consultas que ainda filtram por `owner_id` são **legado pré-F8** e migram conforme os endpoints são tocados.

### Roles (F9)

| Role | Label UI (PT-BR) | Pode ler | Pode escrever | Gerencia membros | Deleta workspace |
|---|---|---|---|---|---|
| `owner` | Responsável | ✅ | ✅ | ✅ | ✅ |
| `member` | Coadministrador | ✅ | ✅ | ❌ | ❌ |
| `viewer` | Acompanha | ✅ | ❌ | ❌ | ❌ |

Definidos em [`workspace_member.py`](../backend/app/models/workspace_member.py):

- `VALID_ROLES` = `{owner, member, viewer}` — aceitos na validação.
- `WRITE_ROLES` = `{owner, member}` — usados por `require_write_role`.
- `MEMBER_ADMIN_ROLES` = `{owner}` — usados por `require_member_admin_role`.

RBAC mais granular (`approver`, `admin`, escopos parciais como "contador vê transações mas não metas") é débito explícito, endereçado quando primeiro cliente consultor pedir.

### Convites (F9)

Fluxo: owner cria convite (`POST /workspaces/{ws}/invitations`) → backend gera token cru (URL-safe, 256 bits) e armazena `SHA-256(token)` no DB → owner copia o link e envia manualmente (WhatsApp/SMS/pessoalmente) → convidado abre `/invite/{token}`, faz login/signup, aceita → `WorkspaceMember` criado.

Regras:

- TTL 72h, uso único, revogável pelo owner.
- Máximo 10 convites pendentes por workspace (rate limit).
- Email do aceite deve bater com o email do convite (case-insensitive).
- Convite como `owner` é bloqueado. Transferência de ownership é débito.
- Token cru **nunca** é persistido — vive apenas no response de criação.

### Token invalidation (F9)

`User.token_version` (int, default 0) é embutido como claim `tv` no JWT. Quando um membro é removido de um workspace, seu `token_version` é incrementado. `get_current_user` rejeita tokens com `tv < user.token_version` → 401 com `code: "token_revoked"`. O frontend detecta esse código e redireciona para login.

### Audit conventions para membership (F9)

Eventos registrados no `AuditLog` existente (sem tabela nova):

| action | Quando | details típico |
|---|---|---|
| `workspace.member.invite` | Convite criado | `{email, role, invitation_id}` |
| `workspace.member.accept` | Convite aceito | `{role}` |
| `workspace.member.revoke_invite` | Convite revogado | `{invitation_id, email}` |
| `workspace.member.role_change` | Role alterada | `{target_user_id, from_role, to_role}` |
| `workspace.member.remove` | Membro removido | `{target_user_id, role}` |

---

## 2. Padrão de endpoint

### ✅ DO — endpoint F8+ (leitura)

```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.core.tenancy import get_current_workspace
from backend.app.models.workspace import Workspace
from backend.app.services import goal_service

router = APIRouter(prefix="/api/workspaces/{workspace_id}")


@router.get("/goals/if")
async def get_if_goal(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    return await goal_service.get_current_goal(workspace.id, "IF", db=db)
```

### ✅ DO — endpoint de escrita (F9+ com RBAC)

Endpoints que modificam dados devem adicionar `require_write_role` (ou
`require_member_admin_role` para gestão de membros) como dependency:

```python
from backend.app.core.tenancy import get_current_workspace, require_write_role

@router.put(
    "/goals/if",
    dependencies=[Depends(require_write_role)],  # ← viewer recebe 403
)
async def upsert_if_goal(
    workspace: Workspace = Depends(get_current_workspace),
    ...
):
    ...
```

Dependencies prontas em [`tenancy.py`](../backend/app/core/tenancy.py):

- `require_write_role` — aceita `owner` e `member`. Para endpoints de escrita genéricos.
- `require_member_admin_role` — aceita só `owner`. Para convidar/remover/mudar role.

### ❌ DON'T — anti-patterns

```python
# ❌ Resolve workspace via user.id (assume 1:1)
@router.get("/api/goals/if")
async def get_if_goal(user: User = Depends(get_current_user), ...):
    ws = await _get_workspace(user, db)  # legado pré-F8
    ...

# ❌ Recebe workspace_id como query param (vazamento via logs/cache)
@router.get("/api/goals/if")
async def get_if_goal(workspace_id: str, ...): ...

# ❌ Recebe workspace_id no body (inconsistente, quebra caching por URL)
class GoalRequest(BaseModel):
    workspace_id: str
    ...
```

---

## 3. Padrão de service

### ✅ DO — service recebe `workspace_id` como 1º argumento

```python
# backend/app/services/goal_service.py
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.goal import Goal


async def get_current_goal(
    workspace_id: str,  # SEMPRE primeiro
    goal_type: str,
    *,
    db: AsyncSession,
) -> Goal | None:
    stmt = select(Goal).where(
        Goal.workspace_id == workspace_id,   # SEMPRE presente
        Goal.type == goal_type,
        Goal.effective_to.is_(None),
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()
```

### ❌ DON'T — confiar em FK sem filtro explícito

```python
# ❌ Assume que Goal.id é globalmente único + não-enumerável.
# Vulnerável a IDOR se goal_id for previsível ou exposto.
async def get_goal_by_id(goal_id: str, db: AsyncSession) -> Goal:
    return await db.get(Goal, goal_id)   # ← sem workspace scope

# ❌ Recebe user em vez de workspace_id
async def get_current_goal(user: User, goal_type: str, db): ...

# ❌ Workspace_id em **kwargs (não é validado pelo lint)
async def get_current_goal(goal_type: str, **kwargs): ...
```

---

## 4. Queries SQLAlchemy — o que o lint valida

O lint [`scripts/lint/check_workspace_scoping.py`](../scripts/lint/check_workspace_scoping.py) (ADR-072) escaneia `backend/app/services/` e `backend/app/api/` procurando:

1. Expressões `select(Model)` onde `Model` tem coluna `workspace_id`.
2. Verifica se algum `.where(...)` ou `.filter(...)` na mesma cadeia referencia `workspace_id`.
3. Se **não** referencia, falha — a menos que tenha comentário `# tenancy: global`.

### ✅ Padrões aceitos

```python
# (a) workspace_id como primeiro filtro
select(Task).where(Task.workspace_id == workspace_id)

# (b) workspace_id combinado com outras condições
select(Task).where(
    Task.workspace_id == workspace_id,
    Task.status == "pending",
)

# (c) múltiplos .where encadeados, um deles com workspace_id
(
    select(Task)
    .where(Task.status == "pending")
    .where(Task.workspace_id == workspace_id)
)

# (d) exceção intencional marcada explicitamente
# tenancy: global — health-check de contagem total
select(Task).where(Task.status == "done")
```

### ❌ Padrões rejeitados

```python
# ❌ (1) .where sem workspace_id
select(Task).where(Task.status == "pending")

# ❌ (2) .where só com FK filha (ID cru do cliente)
select(FamilyMember).where(FamilyMember.id == member_id)

# ❌ (3) Comentário mal escrito (lint exige "tenancy: global" literal)
# tenancy-global
select(Task).where(...)
```

### Padrão builder (tolerado, mas atenção)

O lint **não** falha no padrão builder porque não tem análise de fluxo:

```python
q = select(Task)                                 # ← sem where
q = q.where(Task.workspace_id == workspace_id)   # ← linha separada
q = q.where(Task.status == status)
```

Isso é aceito pelo lint, mas **você** deve garantir que o filtro por `workspace_id` seja SEMPRE aplicado. Se você escrever builder, escreva também um teste de isolamento multi-tenant (§6).

---

## 5. Exceções legítimas — `# tenancy: global`

Use quando a query é intencionalmente global:

- Login/auth (`User`, não-tenant).
- Invite token lookup (`WorkspaceInvitation` por `token_hash` — o token É o fator de autenticação; workspace_id vem do convite).
- Resolução de author names (batch lookup de `User` por IDs para preencher `created_by_name`).
- Métricas internas do produto (contagens agregadas entre tenants, só para admin).
- Jobs de manutenção (migration backfill, audit report do fundador).

```python
async def count_active_users_all_workspaces(db: AsyncSession) -> int:
    # tenancy: global — admin metric, not exposed to end users
    stmt = select(func.count()).select_from(Task).where(Task.status == "active")
    return (await db.execute(stmt)).scalar_one()
```

**Rule of thumb:** se a query vai aparecer em uma rota `/api/workspaces/...`, é tenant-scoped. Se fica em `/api/admin/...` ou em script one-shot, pode ser global.

---

## 6. Testes de isolamento multi-tenant

**Toda rota F8+ tem um teste que:**
1. Cria 2 workspaces com users diferentes.
2. Popula dados distintos em cada.
3. Chama o endpoint com o token do user A, confirma que só vê dados do ws-A.
4. Chama com token do user B, idem.
5. Chama com token do user A mas `workspace_id` do ws-B no path → espera 403.

### Template

```python
# backend/tests/test_goals_api.py
import pytest
from backend.tests import factories


@pytest.mark.asyncio
async def test_goals_tenant_isolation(client, db):
    # Setup: 2 workspaces independentes
    user_a = await factories.make_user(db)
    ws_a = await factories.make_workspace(db, owner=user_a)
    await factories.make_workspace_member(db, workspace=ws_a, user=user_a, role="owner")

    user_b = await factories.make_user(db)
    ws_b = await factories.make_workspace(db, owner=user_b)
    await factories.make_workspace_member(db, workspace=ws_b, user=user_b, role="owner")

    token_a = create_access_token(user_a.id)
    token_b = create_access_token(user_b.id)

    # User A cria goal no ws_a
    resp = await client.put(
        f"/api/workspaces/{ws_a.id}/goals/if",
        json={"renda_passiva_mensal_brl": 30000, "trs_pct": 5.0, ...},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert resp.status_code == 200

    # User B NÃO deve ver
    resp = await client.get(
        f"/api/workspaces/{ws_a.id}/goals/if",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp.status_code == 403  # não 404

    # User A NÃO consegue acessar ws_b
    resp = await client.get(
        f"/api/workspaces/{ws_b.id}/goals/if",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert resp.status_code == 403
```

---

## 7. Checklist de revisão de PR

Antes de aprovar uma PR que adiciona/modifica endpoint ou service:

- [ ] Endpoint usa prefix `/api/workspaces/{workspace_id}/...`
- [ ] Endpoint depende de `get_current_workspace` (não de `_get_workspace(user)` legado)
- [ ] **Endpoints de escrita** têm `dependencies=[Depends(require_write_role)]` (F9)
- [ ] **Endpoints de gestão de membros** têm `dependencies=[Depends(require_member_admin_role)]` (F9)
- [ ] Services recebem `workspace_id` como primeiro argumento
- [ ] Toda query tem `.where(Model.workspace_id == workspace_id)` (ou comentário `# tenancy: global`)
- [ ] Existe teste `test_<endpoint>_tenant_isolation` cobrindo 2 workspaces
- [ ] Teste de role matrix: `viewer` recebe 403 em escritas (F9)
- [ ] `python scripts/lint/check_workspace_scoping.py` passa local
- [ ] Se migrou endpoint legado, removeu a linha correspondente de `scripts/lint/tenancy_baseline.txt`

---

## 8. Migração de endpoints legados

Endpoints pré-F8 (ex: `/api/documents`, `/api/reports`, `/api/config`) ainda usam `_get_workspace(user)` helpers privados duplicados. **Não precisam ser migrados já**, mas:

- Quando tocar o arquivo, migre também.
- Endpoints migrados saem do baseline (`scripts/lint/tenancy_baseline.txt`).
- Deadline rígido de migração completa: **F8.4 (cutover CLI → Web)**.

### Passos da migração de um endpoint legado

1. Ler o endpoint e identificar todas as chamadas `_get_workspace(user, db)`.
2. Criar versão F8: prefix `/api/workspaces/{workspace_id}` + `Depends(get_current_workspace)`.
3. Manter rota legada com deprecation warning (header `Sunset`) por 2 sprints para frontend migrar.
4. Remover rota legada depois que frontend não chama mais.
5. Remover linha do baseline, rodar lint, commit.

---

## 9. Referências

- [ADR-072 — Multi-tenancy strategy](DECISIONS.md#adr-072--multi-tenancy-workspace_id-scoping-explícito--workspacemember-para-multi-família)
- [ADR-078 — Workspace sharing (F9)](DECISIONS.md#adr-078--workspace-sharing-convites-viewer-role-forced-logout)
- [ADR-039 — Dual DB SQLite dev + PostgreSQL prod](DECISIONS.md#adr-039--dual-db-sqlite-dev--postgresql-prod) (rationale para não usar RLS)
- [ADR-075 — Cutover CLI → Web](DECISIONS.md#adr-075--cutover-cli--web-estratégia-de-transição-faseada-com-adapters) (deadline de migração)
- [backend/app/core/tenancy.py](../backend/app/core/tenancy.py) — dependency factory (`get_current_workspace`, `require_role`, `require_write_role`, `require_member_admin_role`)
- [backend/app/models/workspace_invitation.py](../backend/app/models/workspace_invitation.py) — convites (F9)
- [backend/app/services/invitation_service.py](../backend/app/services/invitation_service.py) — ciclo de vida do convite
- [backend/app/services/membership_service.py](../backend/app/services/membership_service.py) — gestão de membros
- [backend/app/services/audit_service.py](../backend/app/services/audit_service.py) — helper de audit log
- [scripts/lint/check_workspace_scoping.py](../scripts/lint/check_workspace_scoping.py) — lint custom
- [scripts/lint/tenancy_baseline.txt](../scripts/lint/tenancy_baseline.txt) — violações legadas toleradas
