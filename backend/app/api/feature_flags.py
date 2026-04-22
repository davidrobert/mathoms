"""Feature flags API — router fino (A6e.4 · ADR-074 · ADR-101 R15/R16).

Delegação para :mod:`backend.app.application.feature_flag`. Flag
desconhecida → ``ValidationError`` → 422 (handler global em ``main.py``).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.feature_flag import (
    FlagsResponse,
    FlagUpdateCommand,
    get_feature_flags,
    set_feature_flag,
)
from backend.app.core.database import get_db
from backend.app.core.tenancy import get_current_workspace
from backend.app.models.workspace import Workspace

router = APIRouter(
    prefix="/workspaces/{workspace_id}/feature-flags",
    tags=["feature-flags"],
)

__all__ = ["router", "FlagsResponse", "FlagUpdateCommand"]


@router.get("", response_model=FlagsResponse)
async def read_flags(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
) -> FlagsResponse:
    return await get_feature_flags(workspace.id, db=db)


# F9+: pode exigir role='owner' para evitar que coadmins desabilitem
# recursos. Hoje segue o padrão dos endpoints F8.x (sem admin-only).
@router.put("/{flag}", response_model=FlagsResponse)
async def update_flag(
    flag: str,
    body: FlagUpdateCommand,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
) -> FlagsResponse:
    return await set_feature_flag(workspace.id, flag, body, db=db)
