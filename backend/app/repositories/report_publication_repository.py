"""ReportPublicationRepository — persistência de ``ReportPublication`` (ADR-186)."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.report_publication import ReportPublication


class ReportPublicationRepository:
    """Single Responsibility: persistência de ``ReportPublication``."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_active(
        self, workspace_id: str, period_yyyymm: str
    ) -> Optional[ReportPublication]:
        """Publicação viva (``unpublished_at IS NULL``) do (workspace, period), se existe."""
        result = await self._session.execute(
            select(ReportPublication).where(
                ReportPublication.workspace_id == workspace_id,
                ReportPublication.period_yyyymm == period_yyyymm,
                ReportPublication.unpublished_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_id(
        self, workspace_id: str, publication_id: str
    ) -> Optional[ReportPublication]:
        result = await self._session.execute(
            select(ReportPublication).where(
                ReportPublication.workspace_id == workspace_id,
                ReportPublication.id == publication_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_workspace(self, workspace_id: str) -> list[ReportPublication]:
        """Histórico completo (vivas + revogadas), ordenado por período desc."""
        result = await self._session.execute(
            select(ReportPublication)
            .where(ReportPublication.workspace_id == workspace_id)
            .order_by(
                ReportPublication.period_yyyymm.desc(),
                ReportPublication.published_at.desc(),
            )
        )
        return list(result.scalars().all())

    async def add(self, publication: ReportPublication) -> ReportPublication:
        self._session.add(publication)
        await self._session.flush()
        return publication
