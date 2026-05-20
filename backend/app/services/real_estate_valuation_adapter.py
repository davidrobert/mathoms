"""Adapter ADR-227 §D4 — boundary DB/SQLAlchemy ↔ RealEstateValuationContext."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.models import DEBT_SOURCE_BASELINE_IRPF_MIGRATION, Debt, PropertyMarketValue
from pipeline.domain.services.patrimonio_types import (
    MarketValueResolution,
    RealEstateValuationContext,
)
from pipeline.domain.services.real_estate_valuation_resolver import compute_staleness_days

_CENTS_TO_BRL = Decimal("0.01")


def load_valuation_context(
    session: Session,
    *,
    workspace_id: str,
    today: Optional[date] = None,
) -> RealEstateValuationContext:
    """Carrega contexto em 2 SELECTs: latest market_value não-superseded por property + soma de Debts por property (com pct)."""
    resolved_today = today or date.today()
    market_values = _load_market_values(session, workspace_id, resolved_today)
    debts_by_property = _load_debts_by_property(session, workspace_id)
    return RealEstateValuationContext(
        market_values=market_values,
        debts_by_property=debts_by_property,
        today=resolved_today,
    )


def _latest_pmv_subquery(workspace_id: str):
    return (
        select(
            PropertyMarketValue.property_id,
            func.max(PropertyMarketValue.valuation_date).label("max_date"),
        )
        .where(
            PropertyMarketValue.workspace_id == workspace_id,
            PropertyMarketValue.superseded_by_id.is_(None),
        )
        .group_by(PropertyMarketValue.property_id)
        .subquery()
    )


def _load_market_values(
    session: Session, workspace_id: str, today: date
) -> dict[str, MarketValueResolution]:
    """Latest non-superseded por property; portátil via subquery MAX(valuation_date)."""
    latest_subq = _latest_pmv_subquery(workspace_id)
    rows = session.execute(
        select(PropertyMarketValue)
        .join(
            latest_subq,
            (PropertyMarketValue.property_id == latest_subq.c.property_id)
            & (PropertyMarketValue.valuation_date == latest_subq.c.max_date),
        )
        .where(
            PropertyMarketValue.workspace_id == workspace_id,
            PropertyMarketValue.superseded_by_id.is_(None),
        )
    ).scalars()
    return {row.property_id: _to_market_resolution(row, today) for row in rows}


def _to_market_resolution(row: PropertyMarketValue, today: date) -> MarketValueResolution:
    valor_brl = (Decimal(row.valor_brl_cents) * _CENTS_TO_BRL).quantize(_CENTS_TO_BRL)
    return MarketValueResolution(
        property_id=row.property_id,
        valor_brl=valor_brl,
        source="mercado",
        valuation_date=row.valuation_date,
        staleness_days=compute_staleness_days(row.valuation_date, today),
    )


def _load_debts_by_property(session: Session, workspace_id: str) -> dict[str, Decimal]:
    """SUM(saldo_devedor_cents * pct/100) por property_id; NULL pct → 100%."""
    rows = session.execute(
        select(Debt.property_id, Debt.saldo_devedor_cents, Debt.percentual_atribuicao_imovel).where(
            Debt.workspace_id == workspace_id,
            Debt.property_id.is_not(None),
        )
    ).all()
    totals: dict[str, Decimal] = {}
    for property_id, saldo_cents, pct in rows:
        pct_decimal = Decimal(str(pct)) if pct is not None else Decimal("100")
        contribution = (Decimal(saldo_cents) * pct_decimal) / Decimal(
            "10000"
        )  # cents * pct/100 → BRL
        totals[property_id] = totals.get(property_id, Decimal("0")) + contribution.quantize(
            _CENTS_TO_BRL
        )
    return totals


def detect_irpf_conflict_ratio(
    soma_debts_brl: Decimal,
    total_dividas_irpf_brl: Decimal,
) -> Optional[Decimal]:
    """Retorna ratio quando soma_debts > 1.1 × IRPF; senão None (ADR-227 §D6 threshold 1.1)."""
    if total_dividas_irpf_brl <= 0:
        return None
    ratio = (soma_debts_brl / total_dividas_irpf_brl).quantize(Decimal("0.01"))
    if ratio > Decimal("1.10"):
        return ratio
    return None


# Marker para reuse em service que precisa filtrar Debt de origem migration.
DEBT_MIGRATION_SOURCE = DEBT_SOURCE_BASELINE_IRPF_MIGRATION
