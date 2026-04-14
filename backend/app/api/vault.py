"""Vault API — CRUD for encrypted PDF passwords."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.core.deps import get_current_user
from backend.app.models.user import User
from backend.app.models.workspace import Workspace
from backend.app.models.password_vault import PasswordVault
from backend.app.schemas.vault import VaultCreateRequest, VaultListResponse, VaultResponse
from backend.app.services.vault import VaultService

router = APIRouter(prefix="/vault", tags=["vault"])


async def _get_workspace(user: User, db: AsyncSession) -> Workspace:
    result = await db.execute(
        select(Workspace).where(Workspace.owner_id == user.id)
    )
    ws = result.scalar_one_or_none()
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace não encontrado")
    return ws


@router.get("/passwords", response_model=VaultListResponse)
async def list_passwords(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ws = await _get_workspace(user, db)
    result = await db.execute(
        select(PasswordVault)
        .where(PasswordVault.workspace_id == ws.id)
        .order_by(PasswordVault.created_at.desc())
    )
    entries = result.scalars().all()
    return VaultListResponse(
        passwords=[VaultResponse.model_validate(e) for e in entries],
        total=len(entries),
    )


@router.post("/passwords", response_model=VaultResponse, status_code=status.HTTP_201_CREATED)
async def create_password(
    body: VaultCreateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ws = await _get_workspace(user, db)
    vault_service = VaultService()
    entry = PasswordVault(
        workspace_id=ws.id,
        label=body.label,
        encrypted_password=vault_service.encrypt(body.password),
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return VaultResponse.model_validate(entry)


@router.delete("/passwords/{password_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_password(
    password_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ws = await _get_workspace(user, db)
    result = await db.execute(
        select(PasswordVault).where(
            PasswordVault.id == password_id,
            PasswordVault.workspace_id == ws.id,
        )
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Senha não encontrada")
    await db.delete(entry)
    await db.commit()
