"""Vault router fino — CRUD de passwords cifrados (A6e.4 · ADR-072 · ADR-101 R15/R16)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.vault import (
    create_password as _create_password,
    delete_password as _delete_password,
    list_passwords as _list_passwords,
)
from backend.app.core.database import get_db
from backend.app.core.tenancy import get_current_workspace, require_write_role
from backend.app.models.workspace import Workspace
from backend.app.schemas.vault import (
    VaultCreateRequest,
    VaultListResponse,
    VaultResponse,
)
from backend.app.services.vault import get_vault

router = APIRouter(
    prefix="/workspaces/{workspace_id}/vault",
    tags=["vault"],
)


@router.get("/passwords", response_model=VaultListResponse)
async def list_passwords(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
) -> VaultListResponse:
    return await _list_passwords(workspace.id, db=db)


@router.post(
    "/passwords",
    response_model=VaultResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_write_role)],
)
async def create_password(
    body: VaultCreateRequest,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
) -> VaultResponse:
    return await _create_password(workspace.id, body, db=db, vault=get_vault())


@router.delete(
    "/passwords/{password_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_write_role)],
)
async def delete_password(
    password_id: str,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
) -> None:
    await _delete_password(workspace.id, password_id, db=db)
