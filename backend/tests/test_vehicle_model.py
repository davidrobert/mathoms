"""A18 L1 P1 (ADR-239) — Vehicle model + UNIQUE/CHECK constraints + identidade imutável."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.security import hash_password
from backend.app.models import (
    CODIGO_RFB_AERONAVE,
    CODIGO_RFB_VEICULO_TERRESTRE,
    User,
    Vehicle,
    Workspace,
)


async def _seed_workspace(db: AsyncSession) -> str:
    user = User(email="vehicle@test.com", hashed_password=hash_password("p"), full_name="V")
    db.add(user)
    await db.flush()
    ws = Workspace(name="WS-V", owner_id=user.id)
    db.add(ws)
    await db.flush()
    return ws.id


def _new_vehicle(
    workspace_id: str,
    *,
    placa: str = "ABC1D23",
    renavam: str = "12345678900",
    codigo_rfb: str = CODIGO_RFB_VEICULO_TERRESTRE,
) -> Vehicle:
    return Vehicle(
        workspace_id=workspace_id,
        placa=placa,
        renavam=renavam,
        marca="Yamaha",
        modelo="NMAX 160",
        ano_modelo=2024,
        ano_fabricacao=2024,
        codigo_rfb=codigo_rfb,
    )


@pytest.mark.asyncio
async def test_create_vehicle_happy_path(db: AsyncSession):
    ws_id = await _seed_workspace(db)
    v = _new_vehicle(ws_id)
    db.add(v)
    await db.flush()
    assert v.id is not None
    assert v.codigo_rfb == CODIGO_RFB_VEICULO_TERRESTRE
    assert v.archived_at is None


@pytest.mark.asyncio
async def test_unique_workspace_placa(db: AsyncSession):
    """ADR-239 D1: identidade imutável (workspace_id, placa) UNIQUE."""
    from sqlalchemy.exc import IntegrityError

    ws_id = await _seed_workspace(db)
    db.add(_new_vehicle(ws_id, placa="DUP1234", renavam="11111111111"))
    await db.flush()
    db.add(_new_vehicle(ws_id, placa="DUP1234", renavam="22222222222"))
    with pytest.raises(IntegrityError):
        await db.flush()
    await db.rollback()


@pytest.mark.asyncio
async def test_check_renavam_length(db: AsyncSession):
    """CHECK: length(renavam) BETWEEN 9 AND 11 (validação regex completa em P2)."""
    from sqlalchemy.exc import IntegrityError

    ws_id = await _seed_workspace(db)
    # Too short — 8 chars
    db.add(_new_vehicle(ws_id, placa="SHORT12", renavam="12345678"))
    with pytest.raises(IntegrityError):
        await db.flush()
    await db.rollback()


@pytest.mark.asyncio
async def test_check_codigo_rfb_enum(db: AsyncSession):
    """ADR-225 invariante: codigo_rfb ∈ {21, 22, 23} para bens (terrestre/aeronave/embarcação)."""
    from sqlalchemy.exc import IntegrityError

    ws_id = await _seed_workspace(db)
    db.add(_new_vehicle(ws_id, placa="BAD1234", codigo_rfb="99"))
    with pytest.raises(IntegrityError):
        await db.flush()
    await db.rollback()


@pytest.mark.asyncio
async def test_aeronave_e_embarcacao_aceitos(db: AsyncSession):
    """codigo_rfb 22 (aeronave) e 23 (embarcação) ficam habilitados — V2 de A18."""
    ws_id = await _seed_workspace(db)
    db.add(
        _new_vehicle(ws_id, placa="AERO1234", renavam="99999999999", codigo_rfb=CODIGO_RFB_AERONAVE)
    )
    await db.flush()


# ─────────────────────── market_rates.reference_month ────────────────────────


@pytest.mark.asyncio
async def test_market_rates_reference_month_opcional(db: AsyncSession):
    """ADR-239 D7: ``reference_month`` nullable para PTAX diário (USD/BRL não usa)."""
    from datetime import date
    from decimal import Decimal

    from backend.app.models.market_rate import MarketRate

    d = date(2026, 5, 21)
    fipe = MarketRate(
        pair="FIPE/NMAX",
        rate=Decimal("18500"),
        observed_at=d,
        reference_month="2026-05",
        source="brasilapi.fipe",
    )
    ptax = MarketRate(pair="USD/BRL", rate=Decimal("5.12"), observed_at=d, source="bcb.ptax")
    db.add_all([fipe, ptax])
    await db.flush()
    assert fipe.reference_month == "2026-05"
    assert ptax.reference_month is None
