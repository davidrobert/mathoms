"""WorkspaceCategoryOverrideRepository — async CRUD (A7.3 · ADR-137)."""

from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.repositories.workspace_category_override_repository import (
    WorkspaceCategoryOverrideRepository,
)
from backend.tests.factories.builders import make_workspace


@pytest_asyncio.fixture
async def workspace_ids(db: AsyncSession) -> tuple[str, str]:
    ws_a = await make_workspace(db, name="WS A")
    ws_b = await make_workspace(db, name="WS B")
    await db.commit()
    return ws_a.id, ws_b.id


@pytest.mark.asyncio
async def test_upsert_creates_new_override(db: AsyncSession, workspace_ids):
    ws_id, _ = workspace_ids
    repo = WorkspaceCategoryOverrideRepository(db)
    ov = await repo.upsert(
        ws_id,
        "moradia",
        label_override="Casa",
        keywords_override=["ALUGUEL"],
    )
    assert ov.id is not None
    assert ov.workspace_id == ws_id
    assert ov.template_key == "moradia"
    assert ov.label_override == "Casa"
    assert list(ov.keywords_override) == ["ALUGUEL"]


@pytest.mark.asyncio
async def test_upsert_updates_existing_override(db: AsyncSession, workspace_ids):
    ws_id, _ = workspace_ids
    repo = WorkspaceCategoryOverrideRepository(db)
    first = await repo.upsert(ws_id, "moradia", label_override="Casa")
    second = await repo.upsert(
        ws_id,
        "moradia",
        label_override="Lar",
        keywords_override=["IPTU"],
    )
    assert first.id == second.id
    assert second.label_override == "Lar"


@pytest.mark.asyncio
async def test_upsert_isolated_per_workspace(db: AsyncSession, workspace_ids):
    ws_a, ws_b = workspace_ids
    repo = WorkspaceCategoryOverrideRepository(db)
    a = await repo.upsert(ws_a, "moradia", label_override="A")
    b = await repo.upsert(ws_b, "moradia", label_override="B")
    assert a.id != b.id
    rows_a = await repo.list_by_workspace(ws_a)
    rows_b = await repo.list_by_workspace(ws_b)
    assert {r.label_override for r in rows_a} == {"A"}
    assert {r.label_override for r in rows_b} == {"B"}


@pytest.mark.asyncio
async def test_get_by_template_key(db: AsyncSession, workspace_ids):
    ws_id, _ = workspace_ids
    repo = WorkspaceCategoryOverrideRepository(db)
    await repo.upsert(ws_id, "moradia", label_override="X")
    found = await repo.get_by_template_key(ws_id, "moradia")
    not_found = await repo.get_by_template_key(ws_id, "naoexiste")
    assert found is not None
    assert found.template_key == "moradia"
    assert not_found is None


@pytest.mark.asyncio
async def test_delete_removes_override(db: AsyncSession, workspace_ids):
    ws_id, _ = workspace_ids
    repo = WorkspaceCategoryOverrideRepository(db)
    ov = await repo.upsert(ws_id, "moradia", label_override="X")
    await repo.delete(ov)
    rows = await repo.list_by_workspace(ws_id)
    assert rows == []


@pytest.mark.asyncio
async def test_disabled_flag_persists(db: AsyncSession, workspace_ids):
    ws_id, _ = workspace_ids
    repo = WorkspaceCategoryOverrideRepository(db)
    ov = await repo.upsert(ws_id, "veiculos", disabled=True)
    assert ov.disabled is True
    refreshed = await repo.get_by_template_key(ws_id, "veiculos")
    assert refreshed.disabled is True


@pytest.mark.asyncio
async def test_monthly_cap_brl_cents_storage(db: AsyncSession, workspace_ids):
    ws_id, _ = workspace_ids
    repo = WorkspaceCategoryOverrideRepository(db)
    ov = await repo.upsert(
        ws_id,
        "alimentacao",
        monthly_cap_brl_cents_override=300000,
    )
    assert ov.monthly_cap_brl_cents_override == 300000
    # Value > int32 max should also work (BigInt)
    ov2 = await repo.upsert(
        ws_id,
        "alimentacao",
        monthly_cap_brl_cents_override=10_000_000_000,
    )
    assert ov2.monthly_cap_brl_cents_override == 10_000_000_000


@pytest.mark.asyncio
async def test_delete_all_in_workspace(db: AsyncSession, workspace_ids):
    ws_id, _ = workspace_ids
    repo = WorkspaceCategoryOverrideRepository(db)
    await repo.upsert(ws_id, "moradia")
    await repo.upsert(ws_id, "alimentacao")
    count = await repo.delete_all_in_workspace(ws_id)
    assert count == 2
    rows = await repo.list_by_workspace(ws_id)
    assert rows == []
