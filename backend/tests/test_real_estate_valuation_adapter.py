"""Integration tests do real_estate_valuation_adapter (ADR-227 §D4)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import event

from backend.app.core.database import SyncSessionLocal
from backend.app.models import (
    DEBT_SOURCE_USER_DECLARED,
    DEBT_TIPO_FINANCIAMENTO_IMOBILIARIO,
    PMV_SOURCE_USER_DECLARED,
    Debt,
    PropertyIdentity,
    PropertyMarketValue,
)
from backend.app.services.real_estate_valuation_adapter import (
    detect_irpf_conflict_ratio,
    load_valuation_context,
)
from backend.tests import factories


async def make_seed_property(db, ws_id: str, descricao: str = "CASA RUA X") -> PropertyIdentity:
    """Allowlisted P1 fixture helper."""
    p = PropertyIdentity(
        workspace_id=ws_id,
        titular_key="david",
        codigo_rfb="12",
        endereco_canonical="rua x",
        first_seen_year=2024,
        descricao_sample=descricao,
    )
    db.add(p)
    await db.flush()
    return p


def make_pmv(ws_id: str, property_id: str, cents: int, valuation_date: date) -> PropertyMarketValue:
    """Allowlisted P1 fixture helper."""
    return PropertyMarketValue(
        workspace_id=ws_id,
        property_id=property_id,
        valor_brl_cents=cents,
        valuation_date=valuation_date,
        source=PMV_SOURCE_USER_DECLARED,
    )


def make_debt_for_property(ws_id: str, property_id: str, cents: int, *, pct=None) -> Debt:
    """Allowlisted P1 fixture helper."""
    kwargs: dict = {
        "workspace_id": ws_id,
        "property_id": property_id,
        "tipo": DEBT_TIPO_FINANCIAMENTO_IMOBILIARIO,
        "descricao": "Debt",
        "saldo_devedor_cents": cents,
        "source": DEBT_SOURCE_USER_DECLARED,
    }
    if pct is not None:
        kwargs["percentual_atribuicao_imovel"] = pct
    return Debt(**kwargs)


@pytest.mark.asyncio
async def test_load_context_returns_empty_when_no_data(db):
    ws = await factories.make_workspace(db)
    await db.commit()
    with SyncSessionLocal() as session:
        ctx = load_valuation_context(session, workspace_id=ws.id, today=date(2026, 5, 20))
    assert ctx.market_values == {}
    assert ctx.debts_by_property == {}
    assert ctx.today == date(2026, 5, 20)


@pytest.mark.asyncio
async def test_load_context_picks_latest_market_value_per_property(db):
    ws = await factories.make_workspace(db)
    p = await make_seed_property(db, ws.id)
    db.add(make_pmv(ws.id, p.id, 100_000_000, date(2025, 1, 1)))
    db.add(make_pmv(ws.id, p.id, 120_000_000, date(2026, 5, 1)))
    await db.commit()

    with SyncSessionLocal() as session:
        ctx = load_valuation_context(session, workspace_id=ws.id, today=date(2026, 5, 20))
    assert p.id in ctx.market_values
    market = ctx.market_values[p.id]
    assert market.valor_brl == Decimal("1200000.00")
    assert market.staleness_days == (date(2026, 5, 20) - date(2026, 5, 1)).days


@pytest.mark.asyncio
async def test_load_context_ignores_superseded_market_value(db):
    ws = await factories.make_workspace(db)
    p = await make_seed_property(db, ws.id)
    old = make_pmv(ws.id, p.id, 100_000_000, date(2025, 1, 1))
    new = make_pmv(ws.id, p.id, 120_000_000, date(2026, 5, 1))
    db.add_all([old, new])
    await db.flush()
    old.superseded_by_id = new.id
    await db.commit()

    with SyncSessionLocal() as session:
        ctx = load_valuation_context(session, workspace_id=ws.id, today=date(2026, 5, 20))
    assert ctx.market_values[p.id].valor_brl == Decimal("1200000.00")


@pytest.mark.asyncio
async def test_load_context_aggregates_debts_per_property_with_pct(db):
    ws = await factories.make_workspace(db)
    p = await make_seed_property(db, ws.id)
    db.add(make_debt_for_property(ws.id, p.id, 30_000_000))
    db.add(make_debt_for_property(ws.id, p.id, 10_000_000, pct=Decimal("50")))
    await db.commit()

    with SyncSessionLocal() as session:
        ctx = load_valuation_context(session, workspace_id=ws.id, today=date(2026, 5, 20))
    # 30_000_000 * 100% + 10_000_000 * 50% = 35_000_000 cents = R$ 350.000,00
    assert ctx.debts_by_property[p.id] == Decimal("350000.00")


@pytest.mark.asyncio
async def test_load_context_ignores_debt_without_property_id(db):
    ws = await factories.make_workspace(db)
    db.add(
        Debt(
            workspace_id=ws.id,
            tipo=DEBT_TIPO_FINANCIAMENTO_IMOBILIARIO,
            descricao="CDC carro",
            saldo_devedor_cents=5_000_000,
            source=DEBT_SOURCE_USER_DECLARED,
        )
    )
    await db.commit()
    with SyncSessionLocal() as session:
        ctx = load_valuation_context(session, workspace_id=ws.id, today=date(2026, 5, 20))
    assert ctx.debts_by_property == {}


def _capture_selects(session, target_list: list[str]):
    def _handler(conn, cursor, statement, parameters, context, executemany):
        if statement.strip().lower().startswith("select"):
            target_list.append(statement)

    return _handler


@pytest.mark.asyncio
async def test_load_context_uses_at_most_two_selects(db):
    """Adapter cap: 2 SELECTs por workspace (ADR-227 §D4 + co-design)."""
    ws = await factories.make_workspace(db)
    await make_seed_property(db, ws.id)
    await db.commit()
    statements: list[str] = []
    with SyncSessionLocal() as session:
        handler = _capture_selects(session, statements)
        event.listen(session.bind, "before_cursor_execute", handler)
        try:
            load_valuation_context(session, workspace_id=ws.id, today=date(2026, 5, 20))
        finally:
            event.remove(session.bind, "before_cursor_execute", handler)
    assert len(statements) == 2, f"esperava 2 SELECTs, obteve {len(statements)}: {statements}"


def test_detect_irpf_conflict_above_threshold():
    """Ratio > 1.1 sinaliza conflito (per-property excede IRPF agregado)."""
    assert detect_irpf_conflict_ratio(Decimal("120000"), Decimal("100000")) == Decimal("1.20")


def test_detect_irpf_conflict_below_threshold_returns_none():
    assert detect_irpf_conflict_ratio(Decimal("105000"), Decimal("100000")) is None
    assert detect_irpf_conflict_ratio(Decimal("100000"), Decimal("100000")) is None


def test_detect_irpf_conflict_with_zero_baseline_returns_none():
    """Sem IRPF baseline (workspace ainda não rodou pipeline) → sem ratio."""
    assert detect_irpf_conflict_ratio(Decimal("50000"), Decimal("0")) is None
