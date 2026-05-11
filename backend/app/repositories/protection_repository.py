"""`ProtectionRepository` — persistência do aggregate `Protection` (ADR-192)."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.protection import Protection


class ProtectionRepository:
    """Single Responsibility: persistência do aggregate ``Protection``."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # -------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------

    async def get_by_id(self, workspace_id: str, protection_id: str) -> Optional[Protection]:
        result = await self._session.execute(
            select(Protection).where(
                Protection.workspace_id == workspace_id,
                Protection.id == protection_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_workspace(self, workspace_id: str) -> list[Protection]:
        """Protections do workspace ordenadas por (category, ends_at asc, created_at desc)."""
        result = await self._session.execute(
            select(Protection)
            .where(Protection.workspace_id == workspace_id)
            .order_by(
                Protection.category.asc(),
                Protection.ends_at.is_(None).asc(),
                Protection.ends_at.asc(),
                Protection.created_at.desc(),
            )
        )
        return list(result.scalars().all())

    async def list_active_by_workspace(self, workspace_id: str) -> list[Protection]:
        """Apenas apólices em estado ``Ativa`` — input principal do bundle."""
        result = await self._session.execute(
            select(Protection)
            .where(
                Protection.workspace_id == workspace_id,
                Protection.status == "Ativa",
            )
            .order_by(
                Protection.category.asc(),
                Protection.ends_at.is_(None).asc(),
                Protection.ends_at.asc(),
            )
        )
        return list(result.scalars().all())

    # -------------------------------------------------------------------
    # Commands
    # -------------------------------------------------------------------

    async def add(self, protection: Protection) -> Protection:
        self._session.add(protection)
        await self._session.flush()
        return protection
