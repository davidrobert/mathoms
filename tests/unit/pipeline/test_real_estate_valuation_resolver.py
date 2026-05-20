"""Resolver puro de valor_efetivo (ADR-227 §D4 + §D5)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pipeline.domain.services.patrimonio_types import (
    MarketValueResolution,
    RealEstateValuationContext,
)
from pipeline.domain.services.real_estate_valuation_resolver import (
    compute_staleness_days,
    resolve_valor_efetivo,
)


def _make_context(*, property_id: str, valor: str, valuation_date: date, today: date):
    res = MarketValueResolution(
        property_id=property_id,
        valor_brl=Decimal(valor),
        source="mercado",
        valuation_date=valuation_date,
        staleness_days=compute_staleness_days(valuation_date, today),
    )
    return RealEstateValuationContext(market_values={property_id: res}, today=today)


def test_resolve_uses_market_value_when_fresh():
    today = date(2026, 5, 20)
    ctx = _make_context(
        property_id="P1",
        valor="1200000.00",
        valuation_date=date(2026, 4, 1),
        today=today,
    )
    valor, source, staleness = resolve_valor_efetivo("P1", Decimal("800000.00"), ctx)
    assert valor == Decimal("1200000.00")
    assert source == "mercado"
    assert staleness == (today - date(2026, 4, 1)).days


def test_resolve_uses_market_value_even_when_stale_signaling_via_staleness():
    """ADR-223 §Riscos: TTL não troca fonte; só sinaliza staleness no payload."""
    today = date(2026, 5, 20)
    ctx = _make_context(
        property_id="P1",
        valor="1200000.00",
        valuation_date=date(2024, 1, 1),
        today=today,  # ~870 dias
    )
    valor, source, staleness = resolve_valor_efetivo("P1", Decimal("800000.00"), ctx)
    assert source == "mercado"
    assert valor == Decimal("1200000.00")
    assert staleness > 365


def test_resolve_falls_back_to_irpf_when_property_id_missing():
    today = date(2026, 5, 20)
    ctx = RealEstateValuationContext(today=today)  # market_values vazio
    valor, source, staleness = resolve_valor_efetivo("P1", Decimal("800000.00"), ctx)
    assert valor == Decimal("800000.00")
    assert source == "irpf"
    assert staleness == 0


def test_resolve_returns_irpf_when_property_id_not_in_context():
    today = date(2026, 5, 20)
    ctx = _make_context(
        property_id="P_OTHER",
        valor="999",
        valuation_date=date(2026, 1, 1),
        today=today,
    )
    valor, source, _ = resolve_valor_efetivo("P_QUERY", Decimal("123.45"), ctx)
    assert source == "irpf"
    assert valor == Decimal("123.45")


def test_compute_staleness_days_handles_future_dates():
    """Data de valuation no futuro (data malformada do user) clamp a 0."""
    assert compute_staleness_days(date(2027, 1, 1), date(2026, 5, 20)) == 0
    assert compute_staleness_days(date(2025, 5, 20), date(2026, 5, 20)) == 365
