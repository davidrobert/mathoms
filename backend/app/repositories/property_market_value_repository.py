"""PropertyMarketValueRepository — append-only (ADR-227 §D2); correção é nova row + ``supersede()``."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.property_market_value import PropertyMarketValue


class PropertyMarketValueRepository:
    """Single Responsibility: persistência append-only de valor de mercado."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # -------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------

    async def latest_by_property(
        self, workspace_id: str, property_id: str
    ) -> Optional[PropertyMarketValue]:
        """Row mais recente não-superseded; empate em ``valuation_date`` desempata por ``created_at``."""
        result = await self._session.execute(
            select(PropertyMarketValue)
            .where(
                PropertyMarketValue.workspace_id == workspace_id,
                PropertyMarketValue.property_id == property_id,
                PropertyMarketValue.superseded_by_id.is_(None),
            )
            .order_by(
                PropertyMarketValue.valuation_date.desc(),
                PropertyMarketValue.created_at.desc(),
            )
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def list_for_property(
        self, workspace_id: str, property_id: str
    ) -> list[PropertyMarketValue]:
        """Histórico completo (inclui supersededs) para auditoria."""
        result = await self._session.execute(
            select(PropertyMarketValue)
            .where(
                PropertyMarketValue.workspace_id == workspace_id,
                PropertyMarketValue.property_id == property_id,
            )
            .order_by(PropertyMarketValue.valuation_date.desc())
        )
        return list(result.scalars().all())

    async def get_by_id(self, workspace_id: str, pmv_id: str) -> Optional[PropertyMarketValue]:
        """Row por id dentro do workspace."""
        result = await self._session.execute(
            select(PropertyMarketValue).where(
                PropertyMarketValue.id == pmv_id,
                PropertyMarketValue.workspace_id == workspace_id,
            )
        )
        return result.scalar_one_or_none()

    # -------------------------------------------------------------------
    # Commands
    # -------------------------------------------------------------------

    async def create(
        self,
        workspace_id: str,
        **fields: Any,
    ) -> PropertyMarketValue:
        """Cria declaração; caller respeita ``UNIQUE (property_id, valuation_date)``."""
        pmv = PropertyMarketValue(workspace_id=workspace_id, **fields)
        self._session.add(pmv)
        await self._session.commit()
        await self._session.refresh(pmv)
        return pmv

    async def supersede(self, old_pmv: PropertyMarketValue, *, by_id: str) -> PropertyMarketValue:
        """Seta ``superseded_by_id`` sem deletar — preserva auditoria (append-only)."""
        old_pmv.superseded_by_id = by_id
        await self._session.commit()
        await self._session.refresh(old_pmv)
        return old_pmv
