"""ADR-227 §D2: model-level tests para PropertyMarketValue."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models import (
    PMV_SOURCE_AVALIACAO_TERCEIROS,
    PMV_SOURCE_USER_DECLARED,
    PropertyIdentity,
    PropertyMarketValue,
    Workspace,
)
from backend.tests.factories.builders import make_workspace


async def make_property_identity(db: AsyncSession, ws: Workspace) -> PropertyIdentity:
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
    return p


def make_pmv(workspace_id: str, property_id: str, **overrides: Any) -> PropertyMarketValue:
    """Allowlisted P1 fixture helper. Defaults sane; overrides via kwargs."""
    fields: dict[str, Any] = {
        "workspace_id": workspace_id,
        "property_id": property_id,
        "valor_brl_cents": 100_000_000,
        "valuation_date": date(2026, 1, 1),
        "source": PMV_SOURCE_USER_DECLARED,
    }
    fields.update(overrides)
    return PropertyMarketValue(**fields)


@pytest.mark.asyncio
async def test_pmv_crud_basic(db: AsyncSession):
    ws = await make_workspace(db)
    p = await make_property_identity(db, ws)
    pmv = make_pmv(ws.id, p.id, valor_brl_cents=120_000_000, valuation_date=date(2026, 5, 20))
    db.add(pmv)
    await db.commit()
    await db.refresh(pmv)
    assert pmv.id is not None
    assert pmv.valor_brl_cents == 120_000_000
    assert pmv.confidence is None
    assert pmv.superseded_by_id is None


@pytest.mark.asyncio
async def test_uq_property_valuation_date_blocks_duplicate(db: AsyncSession):
    """Mesmo property + mesma data → constraint UNIQUE falha (ADR-227 §D2)."""
    ws = await make_workspace(db)
    p = await make_property_identity(db, ws)
    d = date(2026, 5, 20)
    db.add(make_pmv(ws.id, p.id, valuation_date=d))
    await db.commit()
    db.add(make_pmv(ws.id, p.id, valor_brl_cents=110_000_000, valuation_date=d))
    with pytest.raises(Exception):
        await db.commit()


@pytest.mark.asyncio
async def test_chk_pmv_source_rejects_garbage(db: AsyncSession):
    ws = await make_workspace(db)
    p = await make_property_identity(db, ws)
    db.add(make_pmv(ws.id, p.id, valor_brl_cents=100, source="garbage"))
    with pytest.raises(Exception):
        await db.commit()


@pytest.mark.asyncio
async def test_chk_pmv_confidence_rejects_above_1(db: AsyncSession):
    ws = await make_workspace(db)
    p = await make_property_identity(db, ws)
    db.add(
        make_pmv(
            ws.id,
            p.id,
            valor_brl_cents=100,
            source=PMV_SOURCE_AVALIACAO_TERCEIROS,
            confidence=Decimal("1.50"),
        )
    )
    with pytest.raises(Exception):
        await db.commit()


@pytest.mark.asyncio
async def test_chk_pmv_confidence_accepts_null_in_user_declared(db: AsyncSession):
    """V1 user_declared não exige confidence (NULL permitido)."""
    ws = await make_workspace(db)
    p = await make_property_identity(db, ws)
    pmv = make_pmv(ws.id, p.id, valor_brl_cents=100, confidence=None)
    db.add(pmv)
    await db.commit()
    assert pmv.confidence is None


@pytest.mark.asyncio
async def test_supersede_marks_old_without_deletion(db: AsyncSession):
    """Append-only: declaração antiga marcada como superseded; row preservada."""
    ws = await make_workspace(db)
    p = await make_property_identity(db, ws)
    old = make_pmv(ws.id, p.id, valor_brl_cents=100_000_000, valuation_date=date(2025, 1, 1))
    db.add(old)
    await db.commit()
    await db.refresh(old)
    new = make_pmv(ws.id, p.id, valor_brl_cents=120_000_000, valuation_date=date(2026, 5, 20))
    db.add(new)
    await db.commit()
    await db.refresh(new)
    old.superseded_by_id = new.id
    await db.commit()
    await db.refresh(old)
    assert old.superseded_by_id == new.id
    assert old.valor_brl_cents == 100_000_000  # row antiga preserva valor


# ─── FK declarations ────────────────────────────────────────────────────


def test_fk_property_cascade():
    fks = list(PropertyMarketValue.__table__.c.property_id.foreign_keys)
    assert fks and fks[0].ondelete == "CASCADE"


def test_fk_workspace_cascade():
    fks = list(PropertyMarketValue.__table__.c.workspace_id.foreign_keys)
    assert fks and fks[0].ondelete == "CASCADE"


def test_fk_user_set_null():
    fks = list(PropertyMarketValue.__table__.c.created_by_user_id.foreign_keys)
    assert fks and fks[0].ondelete == "SET NULL"
