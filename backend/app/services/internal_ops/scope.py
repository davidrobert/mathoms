"""Scope (PurgeScope) e contexto humano-legível compartilhados (ADR-116)."""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.user import User
from backend.app.models.workspace import Workspace


@dataclass(frozen=True)
class PurgeScope:
    user_id: str | None = None
    workspace_id: str | None = None


@dataclass(frozen=True)
class ScopeContext:
    owner_email: str | None = None
    workspace_names: list[str] = field(default_factory=list)


async def resolve_workspace_ids(db: AsyncSession, scope: PurgeScope) -> list[str]:
    """Retorna lista de workspace_ids alvo. Vazia quando scope sem match."""
    if scope.workspace_id:
        return [scope.workspace_id]
    if scope.user_id:
        rows = await db.execute(
            select(Workspace.id).where(Workspace.owner_id == scope.user_id)
        )
        return [r[0] for r in rows.all()]
    return []


async def _context_by_workspace(db: AsyncSession, ws_id: str) -> ScopeContext:
    row = (
        await db.execute(
            select(Workspace.name, User.email)
            .outerjoin(User, Workspace.owner_id == User.id)
            .where(Workspace.id == ws_id)
        )
    ).first()
    if row is None:
        return ScopeContext()
    ws_name, owner_email = row
    return ScopeContext(
        owner_email=owner_email,
        workspace_names=[ws_name] if ws_name else [],
    )


async def _context_by_user(db: AsyncSession, user_id: str) -> ScopeContext:
    rows = (
        await db.execute(
            select(Workspace.name, User.email)
            .outerjoin(User, Workspace.owner_id == User.id)
            .where(Workspace.owner_id == user_id)
            .order_by(Workspace.created_at.asc())
        )
    ).all()
    if not rows:
        return ScopeContext()
    return ScopeContext(
        owner_email=rows[0][1],
        workspace_names=[name for name, _ in rows if name],
    )


async def resolve_scope_context(db: AsyncSession, scope: PurgeScope) -> ScopeContext:
    """Resolve owner_email + workspace_names para o scope dado."""
    if scope.workspace_id:
        return await _context_by_workspace(db, scope.workspace_id)
    if scope.user_id:
        return await _context_by_user(db, scope.user_id)
    return ScopeContext()
