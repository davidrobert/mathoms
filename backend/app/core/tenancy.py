"""Multi-tenancy dependency — ADR-072.

Toda nova rota de F8+ segue o padrão `/api/workspaces/{workspace_id}/...`
e usa `get_current_workspace` como dependency. Ela:

1. Recebe o `workspace_id` do path param.
2. Recebe o `user` autenticado (via `get_current_user`).
3. Valida que existe uma linha em `workspace_members` relacionando os dois.
4. Devolve o `Workspace` (e injeta em `request.state.workspace`).

Qualquer acesso sem membership → 403 Forbidden (não 404, para evitar
info-leak de existência de workspaces alheios).

## Uso em endpoints novos

```python
from fastapi import APIRouter, Depends
from backend.app.core.tenancy import get_current_workspace
from backend.app.models.workspace import Workspace

router = APIRouter(prefix="/api/workspaces/{workspace_id}")

@router.get("/goals/if")
async def get_if_goal(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    return await goal_service.get_current_goal(workspace.id, "IF")
```

## O que NÃO fazer

- Resolver workspace via `user.id` em endpoints novos. Isso assume 1:1
  user↔workspace, que foi abandonado em F8.
- Aceitar `workspace_id` como query param ou body. Use sempre path param
  para manter a URL como fonte única de identificação do tenant.
- Confiar que a FK do model "é suficiente" — sempre filtre explicitamente
  por `workspace_id` no service layer (ver `docs/tenancy.md`).
"""

from __future__ import annotations

from typing import Callable, Coroutine, Any

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.core.deps import get_current_user
from backend.app.models.user import User
from backend.app.models.workspace import Workspace
from backend.app.models.workspace_member import (
    WorkspaceMember,
    WRITE_ROLES,
    MEMBER_ADMIN_ROLES,
)


async def get_current_workspace(
    workspace_id: str,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Workspace:
    """Resolve o workspace do path param e valida membership do usuário.

    Além de devolver o `Workspace`, injeta em `request.state`:
      - `workspace_id`, `workspace`  — para logs/tracing
      - `workspace_member`           — row de WorkspaceMember do user atual
                                       (reutilizada por `require_role` para
                                       evitar query duplicada)

    Raises:
        HTTPException 403: usuário não é membro do workspace solicitado,
            ou o workspace não existe. Usamos 403 em ambos os casos para
            evitar enumeração de IDs via timing/response diff.
    """
    member_row = await db.execute(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user.id,
        )
    )
    member = member_row.scalar_one_or_none()
    if member is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado ao workspace",
        )

    ws_row = await db.execute(
        select(Workspace).where(
            Workspace.id == workspace_id,
            Workspace.deleted_at.is_(None),  # P1.2 soft-delete filter
        )
    )
    workspace = ws_row.scalar_one_or_none()
    if workspace is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado ao workspace",
        )

    request.state.workspace_id = workspace.id
    request.state.workspace = workspace
    request.state.workspace_member = member
    return workspace


def require_role(
    allowed: frozenset[str],
) -> Callable[..., Coroutine[Any, Any, Workspace]]:
    """Factory de dependency FastAPI: exige que o membership do user
    atual esteja em `allowed`. Use quando um endpoint tem RBAC mais
    estrito que mero "é membro".

    Padrões prontos: `require_write_role`, `require_member_admin_role`.

    Exemplo:

        router.delete(
            "/members/{member_id}",
            dependencies=[Depends(require_member_admin_role)],
        )

    Reutiliza o `WorkspaceMember` já carregado por `get_current_workspace`
    (via `request.state.workspace_member`) — sem query extra.
    """

    async def _dep(
        request: Request,
        workspace: Workspace = Depends(get_current_workspace),
    ) -> Workspace:
        member: WorkspaceMember | None = getattr(
            request.state, "workspace_member", None
        )
        if member is None or member.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Papel insuficiente para esta ação",
            )
        return workspace

    return _dep


# Dependencies prontas — use-as direto em `Depends(...)`
require_write_role = require_role(WRITE_ROLES)
require_member_admin_role = require_role(MEMBER_ADMIN_ROLES)


async def require_workspace_role(
    *,
    workspace: Workspace,
    user: User,
    db: AsyncSession,
    allowed_roles: frozenset[str],
) -> WorkspaceMember:
    """Helper para endpoints que exigem role específica (ex: só `owner`).

    Use em service layer quando a dependency `get_current_workspace` já
    resolveu o workspace mas a ação específica tem RBAC. Ex: deletar
    workspace exige `owner`.

    Retorna a row `WorkspaceMember` para consumo adicional se necessário.
    Levanta HTTP 403 se role não autorizada.
    """
    row = await db.execute(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace.id,
            WorkspaceMember.user_id == user.id,
        )
    )
    member = row.scalar_one_or_none()
    if member is None or member.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Papel insuficiente para esta ação",
        )
    return member
