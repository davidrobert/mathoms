"""Vault API — CRUD for encrypted PDF passwords (tenant-scoped, ADR-072)."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.core.tenancy import get_current_workspace, require_write_role
from backend.app.models.workspace import Workspace
from backend.app.models.password_vault import PasswordVault
from backend.app.schemas.vault import VaultCreateRequest, VaultListResponse, VaultResponse
from backend.app.services.vault import get_vault

router = APIRouter(
    prefix="/workspaces/{workspace_id}/vault",
    tags=["vault"],
)


@router.get("/passwords", response_model=VaultListResponse)
async def list_passwords(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PasswordVault)
        .where(PasswordVault.workspace_id == workspace.id)
        .order_by(PasswordVault.created_at.desc())
    )
    entries = result.scalars().all()
    return VaultListResponse(
        passwords=[VaultResponse.model_validate(e) for e in entries],
        total=len(entries),
    )


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
):
    vault_service = get_vault()
    entry = PasswordVault(
        workspace_id=workspace.id,
        label=body.label,
        encrypted_password=vault_service.encrypt(body.password),
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return VaultResponse.model_validate(entry)


@router.delete(
    "/passwords/{password_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_write_role)],
)
async def delete_password(
    password_id: str,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PasswordVault).where(
            PasswordVault.id == password_id,
            PasswordVault.workspace_id == workspace.id,
        )
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Senha não encontrada")
    await db.delete(entry)
    await db.commit()
