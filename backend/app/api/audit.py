"""Audit API — expõe o audit log do workspace do usuário autenticado.

Rota read-only. Não há endpoint de delete/edit — audit logs são imutáveis
por definição (integridade).

Em produção com volume alto, adicionar: paginação server-side adequada,
filtro por janela de tempo, export CSV. Por ora mantemos simples: últimos
N eventos ordenados por data desc.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.core.deps import get_current_user
from backend.app.models.audit_log import AuditLog
from backend.app.models.user import User
from backend.app.models.workspace import Workspace

router = APIRouter(prefix="/audit", tags=["audit"])


class AuditLogEntry(BaseModel):
    id: str
    action: str
    resource_type: str
    resource_id: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    details: Optional[dict]
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditLogListResponse(BaseModel):
    entries: list[AuditLogEntry]
    total: int


async def _get_workspace(user: User, db: AsyncSession) -> Workspace:
    result = await db.execute(select(Workspace).where(Workspace.owner_id == user.id))
    ws = result.scalar_one_or_none()
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace não encontrado")
    return ws


@router.get("", response_model=AuditLogListResponse)
async def list_audit_logs(
    limit: int = Query(100, ge=1, le=500),
    action: Optional[str] = Query(None, description="Filtrar por ação exata, ex.: document.upload"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lista os audit logs do workspace do usuário autenticado."""
    ws = await _get_workspace(user, db)

    query = select(AuditLog).where(AuditLog.workspace_id == ws.id)
    if action:
        query = query.where(AuditLog.action == action)
    query = query.order_by(AuditLog.created_at.desc()).limit(limit)

    result = await db.execute(query)
    entries = result.scalars().all()

    return AuditLogListResponse(
        entries=[AuditLogEntry.model_validate(e) for e in entries],
        total=len(entries),
    )
