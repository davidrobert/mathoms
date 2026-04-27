"""DecisionRepository — persistência do aggregate ``Decision`` (ADR-136).

Append-only ``decision_events`` é responsabilidade do use case (que
chama ``add_event``). Repo expõe operações primitivas; orchestration
(emit evento + atualizar projeção) vive na application layer.

R13/R14 (ADR-101): toda query inclui ``workspace_id``; repo não commita
(caller é dono do boundary transacional).
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.decision import Decision, DecisionEvent


class DecisionRepository:
    """Single Responsibility: persistência do aggregate ``Decision``."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # -------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------

    async def get_by_id(
        self, workspace_id: str, decision_id: str
    ) -> Optional[Decision]:
        result = await self._session.execute(
            select(Decision).where(
                Decision.workspace_id == workspace_id,
                Decision.id == decision_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_code(
        self, workspace_id: str, code: str
    ) -> Optional[Decision]:
        result = await self._session.execute(
            select(Decision).where(
                Decision.workspace_id == workspace_id,
                Decision.code == code,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_workspace(self, workspace_id: str) -> list[Decision]:
        """Todas as Decisions do workspace, ordenadas por ``code`` ascendente."""
        result = await self._session.execute(
            select(Decision)
            .where(Decision.workspace_id == workspace_id)
            .order_by(Decision.code.asc())
        )
        return list(result.scalars().all())

    async def list_events(self, decision_id: str) -> list[DecisionEvent]:
        result = await self._session.execute(
            select(DecisionEvent)
            .where(DecisionEvent.decision_id == decision_id)
            .order_by(DecisionEvent.occurred_at.asc())
        )
        return list(result.scalars().all())

    # -------------------------------------------------------------------
    # Commands
    # -------------------------------------------------------------------

    async def add(self, decision: Decision) -> Decision:
        self._session.add(decision)
        await self._session.flush()
        return decision

    async def add_event(self, event: DecisionEvent) -> DecisionEvent:
        self._session.add(event)
        await self._session.flush()
        return event
