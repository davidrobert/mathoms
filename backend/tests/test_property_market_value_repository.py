"""Testes do PropertyMarketValueRepository (ADR-227 §D2)."""

from __future__ import annotations

from datetime import date
from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models import (
    PMV_SOURCE_USER_DECLARED,
    PropertyIdentity,
)
from backend.app.repositories.property_market_value_repository import (
    PropertyMarketValueRepository,
)
from backend.tests.factories.builders import make_workspace


def make_pmv_kwargs(**overrides: Any) -> dict[str, Any]:
    """Allowlisted P1 fixture helper. Defaults sane para PropertyMarketValueRepository.create."""
    fields: dict[str, Any] = {
        "valor_brl_cents": 100_000_000,
        "valuation_date": date(2026, 1, 1),
        "source": PMV_SOURCE_USER_DECLARED,
    }
    fields.update(overrides)
    return fields


@pytest_asyncio.fixture
async def workspace_and_property(db: AsyncSession) -> tuple[str, str]:
    ws = await make_workspace(db)
    p = PropertyIdentity(
        workspace_id=ws.id,
        titular_key="titular",
        codigo_rfb="12",
        endereco_canonical="rua x 100",
        first_seen_year=2024,
        descricao_sample="CASA",
    )
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return ws.id, p.id


@pytest.mark.asyncio
async def test_create_and_get_latest(db: AsyncSession, workspace_and_property):
    ws_id, p_id = workspace_and_property
    repo = PropertyMarketValueRepository(db)
    pmv = await repo.create(ws_id, property_id=p_id, **make_pmv_kwargs())
    assert pmv.id is not None
    latest = await repo.latest_by_property(ws_id, p_id)
    assert latest is not None
    assert latest.id == pmv.id


@pytest.mark.asyncio
async def test_latest_by_property_returns_newest_date(db: AsyncSession, workspace_and_property):
    ws_id, p_id = workspace_and_property
    repo = PropertyMarketValueRepository(db)
    await repo.create(ws_id, property_id=p_id, **make_pmv_kwargs(valuation_date=date(2025, 1, 1)))
    newest = await repo.create(
        ws_id,
        property_id=p_id,
        **make_pmv_kwargs(valor_brl_cents=120_000_000, valuation_date=date(2026, 5, 1)),
    )
    await repo.create(ws_id, property_id=p_id, **make_pmv_kwargs(valuation_date=date(2025, 6, 1)))
    latest = await repo.latest_by_property(ws_id, p_id)
    assert latest is not None
    assert latest.id == newest.id
    assert latest.valor_brl_cents == 120_000_000


@pytest.mark.asyncio
async def test_latest_excludes_superseded(db: AsyncSession, workspace_and_property):
    """Row marcada superseded é ignorada pelo latest_by_property."""
    ws_id, p_id = workspace_and_property
    repo = PropertyMarketValueRepository(db)
    older = await repo.create(
        ws_id,
        property_id=p_id,
        **make_pmv_kwargs(valuation_date=date(2025, 1, 1)),
    )
    newer = await repo.create(
        ws_id,
        property_id=p_id,
        **make_pmv_kwargs(valor_brl_cents=120_000_000, valuation_date=date(2026, 5, 1)),
    )
    await repo.supersede(newer, by_id=older.id)
    latest = await repo.latest_by_property(ws_id, p_id)
    assert latest is not None
    assert latest.id == older.id


@pytest.mark.asyncio
async def test_list_for_property_includes_superseded(db: AsyncSession, workspace_and_property):
    """Histórico completo expõe supersededs para auditoria."""
    ws_id, p_id = workspace_and_property
    repo = PropertyMarketValueRepository(db)
    old = await repo.create(
        ws_id, property_id=p_id, **make_pmv_kwargs(valuation_date=date(2025, 1, 1))
    )
    new = await repo.create(
        ws_id,
        property_id=p_id,
        **make_pmv_kwargs(valor_brl_cents=120_000_000, valuation_date=date(2026, 5, 1)),
    )
    await repo.supersede(old, by_id=new.id)
    history = await repo.list_for_property(ws_id, p_id)
    assert {h.id for h in history} == {old.id, new.id}


async def make_property_for(db: AsyncSession, ws_id: str) -> PropertyIdentity:
    p = PropertyIdentity(
        workspace_id=ws_id,
        titular_key="t",
        codigo_rfb="11",
        endereco_canonical="e",
        first_seen_year=2024,
        descricao_sample="x",
    )
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return p


@pytest.mark.asyncio
async def test_latest_isolated_by_workspace(db: AsyncSession):
    """latest_by_property não retorna row de outro workspace."""
    ws = await make_workspace(db)
    other_ws = await make_workspace(db)
    p = await make_property_for(db, ws.id)
    repo = PropertyMarketValueRepository(db)
    await repo.create(ws.id, property_id=p.id, **make_pmv_kwargs(valor_brl_cents=100))
    latest = await repo.latest_by_property(other_ws.id, p.id)
    assert latest is None
