"""Adapter: aplica BaselineInformeMerger via InformeQuery + WisePtaxConverter (A17 L3 P3)."""

from __future__ import annotations

from sqlalchemy.orm import Session as SyncSession

from backend.app.application.informes.informe_query import InformeQuery
from backend.app.repositories.market_rate_repository import MarketRateRepository
from backend.app.services.wise_ptax_converter import WisePtaxConverter
from pipeline.domain.services.baseline_informe_merger import (
    BaselineInformeMerger,
    BaselineMergeResult,
)


def merge_baseline_with_informes_pf(
    consolidated: dict, *, workspace_id: str, db: SyncSession
) -> BaselineMergeResult:
    """Aplica saldos_31_12 dos informes financeiro_pf ao baseline (ADR-238 D5)."""
    informes = InformeQuery(db).list_for_workspace(workspace_id, tipo_informe="financeiro_pf")
    if not informes:
        return BaselineMergeResult(baseline=consolidated)
    converter = WisePtaxConverter(MarketRateRepository(db))
    merger = BaselineInformeMerger(ptax_getter=converter.get_quote_or_none)
    return merger.merge(consolidated, informes)
