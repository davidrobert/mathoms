"""Calculator com ``valuation_context`` (ADR-227 §D3) — net IF + paridade legado."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pipeline.domain.services.patrimonio_calculator import PatrimonioCalculator
from pipeline.domain.services.patrimonio_types import (
    MarketValueResolution,
    MemberIdentity,
    PatrimonioConfig,
    PatrimonioInputs,
    RealEstateValuationContext,
)


def _make_baseline(
    titular_key: str, imoveis: list[dict], total_dividas_brl: Decimal = Decimal("0")
) -> dict:
    total_bens = sum(im.get("valor_31_12_ano_base", 0) for im in imoveis)
    return {
        "pipeline_stage": "E1.5_Baseline_Patrimonial",
        "members": {
            titular_key: {
                "total_bens": total_bens,
                "total_dividas": float(total_dividas_brl),
                "bens": {"imoveis": imoveis},
            }
        },
    }


def _config_with_locado(titular_key: str, property_id: str) -> PatrimonioConfig:
    return PatrimonioConfig(
        members=MemberIdentity(
            titular_key=titular_key,
            conjuge_key="",
            titular_nome=titular_key.title(),
            conjuge_nome="",
        ),
        property_classification_overrides={property_id: "locado"},
        include_real_estate_in_if=True,
    )


def _market(
    property_id: str, valor: str, *, valuation_date: date, staleness_days: int = 49
) -> MarketValueResolution:
    return MarketValueResolution(
        property_id=property_id,
        valor_brl=Decimal(valor),
        source="mercado",
        valuation_date=valuation_date,
        staleness_days=staleness_days,
    )


def _ctx_with(
    market: MarketValueResolution | None, debt: Decimal, today: date
) -> RealEstateValuationContext:
    mv = {market.property_id: market} if market else {}
    dbts = {market.property_id: debt} if market else {}
    return RealEstateValuationContext(market_values=mv, debts_by_property=dbts, today=today)


def test_calculator_uses_gross_when_no_valuation_context_retrocompat():
    """Workspace sem context (Onda 2 não rodada) → cat_2 bruto = valor IRPF."""
    p_id = "PID-1"
    imovel = {"property_id": p_id, "valor_31_12_ano_base": 800_000.0}
    inputs = PatrimonioInputs(baseline=_make_baseline("david", [imovel]))
    calc = PatrimonioCalculator(_config_with_locado("david", p_id))
    result = calc.calculate(inputs)
    # Sem context, cat_2 entra bruto em investivel_efetivo.
    assert result["imoveis_geradores"] == 800_000.0
    assert result["investivel_efetivo"] == 800_000.0


def test_calculator_uses_net_when_valuation_context_present():
    """Com context: valor_mercado + saldo_devedor → líquido econômico no IF."""
    p_id = "PID-1"
    imovel = {"property_id": p_id, "valor_31_12_ano_base": 800_000.0}
    today = date(2026, 5, 20)
    ctx = _ctx_with(
        _market(p_id, "1200000.00", valuation_date=date(2026, 4, 1)), Decimal("300000.00"), today
    )
    inputs = PatrimonioInputs(baseline=_make_baseline("david", [imovel]), valuation_context=ctx)
    result = PatrimonioCalculator(_config_with_locado("david", p_id)).calculate(inputs)
    assert result["imoveis_geradores"] == 800_000.0  # Tabela cat_2 preserva bruto IRPF.
    assert result["investivel_efetivo"] == 900_000.0  # 1.200.000 − 300.000 = 900.000.


def test_calculator_fallback_irpf_when_property_not_in_context():
    """Property sem market_value → resolver retorna IRPF; subtrai debt se houver."""
    p_id = "PID-1"
    imovel = {"property_id": p_id, "valor_31_12_ano_base": 800_000.0}
    today = date(2026, 5, 20)
    # Context vazio em market_values; debt presente.
    ctx = RealEstateValuationContext(
        market_values={},
        debts_by_property={p_id: Decimal("200000.00")},
        today=today,
    )
    inputs = PatrimonioInputs(
        baseline=_make_baseline("david", [imovel]),
        valuation_context=ctx,
    )
    calc = PatrimonioCalculator(_config_with_locado("david", p_id))
    result = calc.calculate(inputs)
    # Líquido = max(0, 800.000 − 200.000) = 600.000
    assert result["investivel_efetivo"] == 600_000.0


def test_calculator_floors_at_zero_when_debt_exceeds_value():
    """Saldo > valor (upside-down loan) → líquido floor 0, não negativo."""
    p_id = "PID-1"
    imovel = {"property_id": p_id, "valor_31_12_ano_base": 100_000.0}
    today = date(2026, 5, 20)
    ctx = RealEstateValuationContext(
        market_values={},
        debts_by_property={p_id: Decimal("150000.00")},
        today=today,
    )
    inputs = PatrimonioInputs(
        baseline=_make_baseline("david", [imovel]),
        valuation_context=ctx,
    )
    calc = PatrimonioCalculator(_config_with_locado("david", p_id))
    result = calc.calculate(inputs)
    assert result["investivel_efetivo"] == 0.0


def test_calculator_split_imoveis_preserves_bruto_in_table():
    """ADR-227 §D3: tabela cat_2 sempre bruto; líquido só em investivel_efetivo."""
    p_id = "PID-1"
    imovel = {"property_id": p_id, "valor_31_12_ano_base": 800_000.0}
    ctx = _ctx_with(
        _market(p_id, "1200000.00", valuation_date=date(2026, 4, 1)),
        Decimal("300000.00"),
        date(2026, 5, 20),
    )
    inputs = PatrimonioInputs(baseline=_make_baseline("david", [imovel]), valuation_context=ctx)
    result = PatrimonioCalculator(_config_with_locado("david", p_id)).calculate(inputs)
    assert result["imoveis_geradores"] == 800_000.0  # bruto IRPF na tabela
    assert result["investivel_efetivo"] == 900_000.0  # líquido econômico no IF
