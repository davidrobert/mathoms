"""Leitura sync de ``economic_assumptions`` + override por workspace (ADR-219 D3)."""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.economic_assumption import (
    EconomicAssetClass,
    EconomicAssumption,
    WorkspaceEconomicAssumptionOverride,
)


class EconomicAssumptionRepository:
    """Leitura sync de ``economic_assumptions`` + override (consumido pelo worker)."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_active_classes(self) -> list[EconomicAssetClass]:
        """Classes AUVP ativas (não-deprecated) ordenadas por ``sort_order``."""
        stmt = (
            select(EconomicAssetClass)
            .where(EconomicAssetClass.active.is_(True))
            .order_by(EconomicAssetClass.sort_order)
        )
        return list(self._session.execute(stmt).scalars().all())

    def list_all_classes(self) -> list[EconomicAssetClass]:
        """Todas as classes (ativas + deprecadas), para audit/admin."""
        stmt = select(EconomicAssetClass).order_by(EconomicAssetClass.sort_order)
        return list(self._session.execute(stmt).scalars().all())

    def list_global_vigentes_em(self, as_of: date) -> list[EconomicAssumption]:
        """Premissas globais vigentes em ``as_of`` (ignora override por workspace)."""
        stmt = (
            select(EconomicAssumption)
            .where(EconomicAssumption.effective_from <= as_of)
            .where(
                (EconomicAssumption.effective_to.is_(None))
                | (EconomicAssumption.effective_to >= as_of)
            )
            .order_by(EconomicAssumption.classe_auvp, EconomicAssumption.effective_from.desc())
        )
        return list(self._session.execute(stmt).scalars().all())

    def list_workspace_overrides_vigentes_em(
        self, workspace_id: str, as_of: date
    ) -> list[WorkspaceEconomicAssumptionOverride]:
        """Overrides de ``workspace_id`` vigentes em ``as_of``."""
        stmt = (
            select(WorkspaceEconomicAssumptionOverride)
            .where(WorkspaceEconomicAssumptionOverride.workspace_id == workspace_id)
            .where(WorkspaceEconomicAssumptionOverride.effective_from <= as_of)
            .where(
                (WorkspaceEconomicAssumptionOverride.effective_to.is_(None))
                | (WorkspaceEconomicAssumptionOverride.effective_to >= as_of)
            )
            .order_by(
                WorkspaceEconomicAssumptionOverride.classe_auvp,
                WorkspaceEconomicAssumptionOverride.effective_from.desc(),
            )
        )
        return list(self._session.execute(stmt).scalars().all())
