"""ADR-227 §D1: model-level tests para Debt — constraints + FK declarations (FK pragma OFF em SQLite; CHECK/UNIQUE honrados real)."""

from __future__ import annotations

from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models import (
    DEBT_SOURCE_BASELINE_IRPF_MIGRATION,
    DEBT_SOURCE_USER_DECLARED,
    DEBT_TIPO_CARTAO_ROTATIVO,
    DEBT_TIPO_FINANCIAMENTO_IMOBILIARIO,
    DEBT_TIPO_OUTRO,
    Debt,
    PropertyIdentity,
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


def make_debt(workspace_id: str, **overrides: Any) -> Debt:
    """Allowlisted P1 fixture helper. Defaults sane; overrides via kwargs."""
    fields: dict[str, Any] = {
        "workspace_id": workspace_id,
        "tipo": DEBT_TIPO_OUTRO,
        "descricao": "teste",
        "saldo_devedor_cents": 1_000,
        "source": DEBT_SOURCE_USER_DECLARED,
    }
    fields.update(overrides)
    return Debt(**fields)


@pytest.mark.asyncio
async def test_debt_crud_basic(db: AsyncSession):
    ws = await make_workspace(db)
    p = await make_property_identity(db, ws)
    debt = make_debt(
        ws.id,
        property_id=p.id,
        tipo=DEBT_TIPO_FINANCIAMENTO_IMOBILIARIO,
        descricao=None,
        saldo_devedor_cents=30_000_000,
    )
    db.add(debt)
    await db.commit()
    await db.refresh(debt)
    assert debt.id is not None
    assert debt.saldo_devedor_cents == 30_000_000
    assert debt.needs_review is False


@pytest.mark.asyncio
async def test_chk_debt_tipo_rejects_garbage(db: AsyncSession):
    ws = await make_workspace(db)
    db.add(make_debt(ws.id, tipo="garbage_tipo"))
    with pytest.raises(Exception):
        await db.commit()


@pytest.mark.asyncio
async def test_chk_debt_source_rejects_garbage(db: AsyncSession):
    ws = await make_workspace(db)
    db.add(make_debt(ws.id, source="garbage_source"))
    with pytest.raises(Exception):
        await db.commit()


@pytest.mark.asyncio
async def test_chk_debt_identity_rejects_all_null(db: AsyncSession):
    """Debt sem member, sem property, sem descrição → CHECK falha."""
    ws = await make_workspace(db)
    db.add(make_debt(ws.id, descricao=None))
    with pytest.raises(Exception):
        await db.commit()


@pytest.mark.asyncio
async def test_chk_debt_identity_accepts_only_descricao(db: AsyncSession):
    """Apenas descrição é identidade suficiente."""
    ws = await make_workspace(db)
    debt = make_debt(ws.id, descricao="Empréstimo pessoal banco X")
    db.add(debt)
    await db.commit()
    assert debt.id is not None


@pytest.mark.asyncio
async def test_chk_debt_pct_atribuicao_rejects_zero(db: AsyncSession):
    ws = await make_workspace(db)
    db.add(make_debt(ws.id, percentual_atribuicao_imovel=0))
    with pytest.raises(Exception):
        await db.commit()


@pytest.mark.asyncio
async def test_chk_debt_pct_atribuicao_rejects_above_100(db: AsyncSession):
    ws = await make_workspace(db)
    db.add(make_debt(ws.id, percentual_atribuicao_imovel=101))
    with pytest.raises(Exception):
        await db.commit()


@pytest.mark.asyncio
async def test_partial_unique_migration_source_blocks_duplicate(db: AsyncSession):
    """Idempotência da migration (Onda 2): re-run com mesma chave falha."""
    ws = await make_workspace(db)
    common = {
        "source": DEBT_SOURCE_BASELINE_IRPF_MIGRATION,
        "migration_source_key": "ws_member_a",
        "needs_review": True,
    }
    db.add(make_debt(ws.id, descricao="Migrado", **common))
    await db.commit()
    db.add(make_debt(ws.id, descricao="Migrado-dup", saldo_devedor_cents=2_000, **common))
    with pytest.raises(Exception):
        await db.commit()


@pytest.mark.asyncio
async def test_partial_unique_only_restricts_migration_source(db: AsyncSession):
    """Partial só restringe baseline_irpf_migration; user_declared pode repetir migration_source_key."""
    ws = await make_workspace(db)
    db.add(make_debt(ws.id, descricao="A", migration_source_key="user_key"))
    db.add(make_debt(ws.id, descricao="B", migration_source_key="user_key"))
    await db.commit()  # Não estoura.


@pytest.mark.asyncio
async def test_bigint_cents_handles_large_amount(db: AsyncSession):
    """Roundtrip de R$ 999.999.999,99 (~1e10 cents) cabe em BigInteger."""
    ws = await make_workspace(db)
    big = 99_999_999_999
    debt = make_debt(ws.id, saldo_devedor_cents=big)
    db.add(debt)
    await db.commit()
    await db.refresh(debt)
    assert debt.saldo_devedor_cents == big


@pytest.mark.asyncio
async def test_cartao_rotativo_distinct_from_rotativo(db: AsyncSession):
    """Enum aceita cartao_rotativo e rotativo como valores distintos (ADR-227 §D1)."""
    ws = await make_workspace(db)
    d1 = make_debt(ws.id, tipo=DEBT_TIPO_CARTAO_ROTATIVO, descricao="cartao")
    db.add(d1)
    await db.commit()
    assert d1.tipo == DEBT_TIPO_CARTAO_ROTATIVO


# ─── FK declarations (SQLite FK pragma OFF — testa declaração, não cascade) ───


def test_fk_workspace_cascade():
    fks = list(Debt.__table__.c.workspace_id.foreign_keys)
    assert fks and fks[0].ondelete == "CASCADE"


def test_fk_family_member_set_null():
    fks = list(Debt.__table__.c.family_member_id.foreign_keys)
    assert fks and fks[0].ondelete == "SET NULL"


def test_fk_property_restrict():
    """ON DELETE RESTRICT impede órfão silencioso (ADR-227 §D1)."""
    fks = list(Debt.__table__.c.property_id.foreign_keys)
    assert fks and fks[0].ondelete == "RESTRICT"
