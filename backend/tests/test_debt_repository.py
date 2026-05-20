"""Testes do DebtRepository (ADR-227 §D1)."""

from __future__ import annotations

from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models import (
    DEBT_SOURCE_BASELINE_IRPF_MIGRATION,
    DEBT_SOURCE_USER_DECLARED,
    DEBT_TIPO_FINANCIAMENTO_IMOBILIARIO,
    DEBT_TIPO_OUTRO,
    PropertyIdentity,
)
from backend.app.repositories.debt_repository import DebtRepository
from backend.tests.factories.builders import make_workspace


def make_debt_kwargs(**overrides: Any) -> dict[str, Any]:
    """Allowlisted P1 fixture helper. Defaults sane para DebtRepository.create."""
    fields: dict[str, Any] = {
        "tipo": DEBT_TIPO_OUTRO,
        "descricao": "teste",
        "saldo_devedor_cents": 1_000,
        "source": DEBT_SOURCE_USER_DECLARED,
    }
    fields.update(overrides)
    return fields


@pytest_asyncio.fixture
async def two_workspaces(db: AsyncSession) -> tuple[str, str]:
    ws_a = await make_workspace(db, name="A")
    ws_b = await make_workspace(db, name="B")
    await db.commit()
    return ws_a.id, ws_b.id


@pytest.mark.asyncio
async def test_create_and_get(db: AsyncSession, two_workspaces):
    ws_id, _ = two_workspaces
    repo = DebtRepository(db)
    created = await repo.create(
        ws_id, **make_debt_kwargs(descricao="CDC carro", saldo_devedor_cents=2_500_000)
    )
    assert created.id is not None
    fetched = await repo.get_by_id(ws_id, created.id)
    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.saldo_devedor_cents == 2_500_000


@pytest.mark.asyncio
async def test_get_by_id_isolated_by_workspace(db: AsyncSession, two_workspaces):
    ws_a, ws_b = two_workspaces
    repo = DebtRepository(db)
    d = await repo.create(ws_a, **make_debt_kwargs(descricao="x"))
    # Mesma id buscada com workspace errado → None.
    fetched = await repo.get_by_id(ws_b, d.id)
    assert fetched is None


@pytest.mark.asyncio
async def test_list_for_workspace(db: AsyncSession, two_workspaces):
    ws_a, ws_b = two_workspaces
    repo = DebtRepository(db)
    await repo.create(ws_a, **make_debt_kwargs(descricao="a1"))
    await repo.create(ws_a, **make_debt_kwargs(descricao="a2", saldo_devedor_cents=2))
    await repo.create(ws_b, **make_debt_kwargs(descricao="b1", saldo_devedor_cents=3))
    debts_a = await repo.list_for_workspace(ws_a)
    debts_b = await repo.list_for_workspace(ws_b)
    assert {d.descricao for d in debts_a} == {"a1", "a2"}
    assert {d.descricao for d in debts_b} == {"b1"}


async def make_property_for_workspace(db: AsyncSession, ws_id: str) -> PropertyIdentity:
    p = PropertyIdentity(
        workspace_id=ws_id,
        titular_key="t",
        codigo_rfb="11",
        endereco_canonical="end",
        first_seen_year=2024,
        descricao_sample="x",
    )
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return p


@pytest.mark.asyncio
async def test_list_for_property(db: AsyncSession, two_workspaces):
    ws_id, _ = two_workspaces
    p = await make_property_for_workspace(db, ws_id)
    repo = DebtRepository(db)
    await repo.create(
        ws_id,
        **make_debt_kwargs(
            property_id=p.id,
            tipo=DEBT_TIPO_FINANCIAMENTO_IMOBILIARIO,
            descricao=None,
            saldo_devedor_cents=30_000_000,
        ),
    )
    await repo.create(ws_id, **make_debt_kwargs(descricao="solto"))
    debts = await repo.list_for_property(ws_id, p.id)
    assert len(debts) == 1
    assert debts[0].property_id == p.id


@pytest.mark.asyncio
async def test_list_needs_review(db: AsyncSession, two_workspaces):
    ws_id, _ = two_workspaces
    repo = DebtRepository(db)
    await repo.create(ws_id, **make_debt_kwargs(descricao="a", needs_review=True))
    await repo.create(ws_id, **make_debt_kwargs(descricao="b", needs_review=False))
    pending = await repo.list_needs_review(ws_id)
    assert len(pending) == 1
    assert pending[0].descricao == "a"


@pytest.mark.asyncio
async def test_update_changes_field(db: AsyncSession, two_workspaces):
    ws_id, _ = two_workspaces
    repo = DebtRepository(db)
    d = await repo.create(ws_id, **make_debt_kwargs(descricao="orig"))
    updated = await repo.update(d, saldo_devedor_cents=2_000, needs_review=True)
    assert updated.saldo_devedor_cents == 2_000
    assert updated.needs_review is True


@pytest.mark.asyncio
async def test_delete_removes_row(db: AsyncSession, two_workspaces):
    ws_id, _ = two_workspaces
    repo = DebtRepository(db)
    d = await repo.create(ws_id, **make_debt_kwargs(descricao="x"))
    await repo.delete(d)
    assert await repo.get_by_id(ws_id, d.id) is None


def _migration_row(ws_id: str, i: int) -> dict[str, Any]:
    return {
        "workspace_id": ws_id,
        **make_debt_kwargs(
            descricao=f"Migrado {i}",
            saldo_devedor_cents=1_000 * (i + 1),
            source=DEBT_SOURCE_BASELINE_IRPF_MIGRATION,
            migration_source_key=f"key_{i}",
            needs_review=True,
        ),
    }


@pytest.mark.asyncio
async def test_bulk_create_from_migration(db: AsyncSession, two_workspaces):
    ws_id, _ = two_workspaces
    repo = DebtRepository(db)
    n = await repo.bulk_create_from_migration([_migration_row(ws_id, i) for i in range(3)])
    assert n == 3
    debts = await repo.list_for_workspace(ws_id)
    assert len(debts) == 3
    assert all(d.needs_review for d in debts)
