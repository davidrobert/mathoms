"""Feature flags API (ADR-074).

Endpoints:
  GET  /workspaces/{ws}/feature-flags        — lê flags efetivas (defaults+overrides)
  PUT  /workspaces/{ws}/feature-flags/{flag} — set override (só owner/admin)

O frontend consulta GET ao montar o AppShell para decidir se mostra
itens de nav (ex: "Plano de Ação" aparece só se `tasks_v2_enabled`).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.core.tenancy import get_current_workspace
from backend.app.models.workspace import Workspace
from backend.app.services import feature_flags_service

router = APIRouter(
    prefix="/workspaces/{workspace_id}/feature-flags",
    tags=["feature-flags"],
)


class FlagsResponse(BaseModel):
    flags: dict[str, bool]


class FlagUpdateRequest(BaseModel):
    enabled: bool


@router.get("", response_model=FlagsResponse)
async def read_flags(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    flags = await feature_flags_service.get_flags(workspace.id, db=db)
    return FlagsResponse(flags=flags)


@router.put("/{flag}", response_model=FlagsResponse)
async def update_flag(
    flag: str,
    body: FlagUpdateRequest,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    """Set override workspace-level para uma flag.

    Nota: este endpoint NÃO tem `require_member_admin_role` por enquanto
    para manter compatibilidade com o padrão dos outros endpoints F8.x.
    Em F9+ (RBAC granular completo), pode exigir role='owner' para
    evitar que coadministradores desabilitem recursos.
    """
    try:
        flags = await feature_flags_service.set_flag(
            workspace.id, flag, body.enabled, db=db
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    await db.commit()
    return FlagsResponse(flags=flags)
