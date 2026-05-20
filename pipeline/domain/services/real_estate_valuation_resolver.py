"""Resolver puro de ``valor_efetivo`` de imóvel (ADR-227 §D4 + §D5)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Literal

from pipeline.domain.services.patrimonio_types import RealEstateValuationContext


def resolve_valor_efetivo(
    property_id: str,
    valor_irpf_brl: Decimal,
    context: RealEstateValuationContext,
    *,
    ttl_days: int = 365,
) -> tuple[Decimal, Literal["mercado", "irpf"], int]:
    """Cascade ``property_market_value`` (qualquer idade) || ``valor_irpf_brl``; ``ttl_days`` só sinaliza staleness, não troca fonte (ADR-223)."""
    market = context.market_values.get(property_id)
    if market is None:
        return valor_irpf_brl, "irpf", 0
    return market.valor_brl, "mercado", market.staleness_days


def compute_staleness_days(valuation_date: date, today: date) -> int:
    """Helper exposto para uso do adapter ao montar ``MarketValueResolution``."""
    delta = today - valuation_date
    return max(0, delta.days)
