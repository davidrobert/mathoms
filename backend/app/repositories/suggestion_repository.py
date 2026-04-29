"""SuggestionRepository — persistência do aggregate ``Suggestion`` (ADR-153).

Repo expõe primitivas; orchestration (transição de status, criação de
Decision quando aceita) vive na application layer.

R13/R14 (ADR-101): toda query inclui ``workspace_id``; repo não commita
(caller é dono do boundary transacional).
"""

from __future__ import annotations

from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.suggestion import Suggestion


class SuggestionRepository:
    """Single Responsibility: persistência do aggregate ``Suggestion``."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # -------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------

    async def get_by_id(
        self, workspace_id: str, suggestion_id: str
    ) -> Optional[Suggestion]:
        result = await self._session.execute(
            select(Suggestion).where(
                Suggestion.workspace_id == workspace_id,
                Suggestion.id == suggestion_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_dedup_key(
        self,
        workspace_id: str,
        dedup_key: str,
        statuses: Optional[Sequence[str]] = None,
    ) -> list[Suggestion]:
        """Busca por dedup_key (opcionalmente filtrando por status). Sem
        filtro retorna todas — a regra de "respeitar Descartada" vive no
        gerador (`pipeline.domain.services.suggestion_generator`)."""
        stmt = select(Suggestion).where(
            Suggestion.workspace_id == workspace_id,
            Suggestion.dedup_key == dedup_key,
        )
        if statuses:
            stmt = stmt.where(Suggestion.status.in_(list(statuses)))
        stmt = stmt.order_by(Suggestion.created_at.desc())
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_workspace(
        self, workspace_id: str, status: Optional[str] = None
    ) -> list[Suggestion]:
        stmt = select(Suggestion).where(Suggestion.workspace_id == workspace_id)
        if status is not None:
            stmt = stmt.where(Suggestion.status == status)
        stmt = stmt.order_by(Suggestion.created_at.desc())
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def count_by_workspace(
        self, workspace_id: str, status: Optional[str] = None
    ) -> int:
        items = await self.list_by_workspace(workspace_id, status=status)
        return len(items)

    # -------------------------------------------------------------------
    # Commands
    # -------------------------------------------------------------------

    async def add(self, suggestion: Suggestion) -> Suggestion:
        self._session.add(suggestion)
        await self._session.flush()
        return suggestion
