"""RiskRepository — persistência do aggregate ``Risk`` (ADR-178).

R13/R14 (ADR-101): toda query inclui ``workspace_id``; repo não commita
(caller é dono do boundary transacional). Diferente de ``Decision``, não
há event log — Risk é CRUD com ``updated_at`` (v1, ADR-178 §"Trade-offs").
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import case, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.risk import Risk

# Ordens canônicas para ranking (lower = mais grave). Mantidos como tuplas
# de pares (valor, rank) para alimentar SQL CASE; rank menor = topo.
_IMPACT_RANK = {"crítico": 0, "alto": 1, "médio": 2, "baixo": 3}
_PROBABILITY_RANK = {"alta": 0, "média": 1, "baixa": 2}


class RiskRepository:
    """Single Responsibility: persistência do aggregate ``Risk``."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # -------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------

    async def get_by_id(self, workspace_id: str, risk_id: str) -> Optional[Risk]:
        result = await self._session.execute(
            select(Risk).where(
                Risk.workspace_id == workspace_id,
                Risk.id == risk_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_code(self, workspace_id: str, code: str) -> Optional[Risk]:
        result = await self._session.execute(
            select(Risk).where(
                Risk.workspace_id == workspace_id,
                Risk.code == code,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_workspace(self, workspace_id: str) -> list[Risk]:
        """Risks do workspace ordenados por (impact_level → probability).

        Mais críticos primeiro. ``probability=None`` ordena após valores
        preenchidos. ``code`` é tiebreaker estável.
        """
        impact_order = case(_IMPACT_RANK, value=Risk.impact_level, else_=99)
        prob_order = case(_PROBABILITY_RANK, value=Risk.probability, else_=99)
        result = await self._session.execute(
            select(Risk)
            .where(Risk.workspace_id == workspace_id)
            .order_by(impact_order.asc(), prob_order.asc(), Risk.code.asc())
        )
        return list(result.scalars().all())

    # -------------------------------------------------------------------
    # Commands
    # -------------------------------------------------------------------

    async def add(self, risk: Risk) -> Risk:
        self._session.add(risk)
        await self._session.flush()
        return risk

    async def delete(self, risk: Risk) -> None:
        await self._session.delete(risk)
        await self._session.flush()
