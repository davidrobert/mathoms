"""Testes do `memory_confirmation_service` (ADR-262): confirm + get_status + stale."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from backend.app.models.workspace_memory_confirmation import WorkspaceMemoryConfirmation
from backend.app.repositories.workspace_memory_confirmation_repository import (
    WorkspaceMemoryConfirmationRepository,
    is_stale_by_age,
    is_stale_by_value,
)
from backend.app.services.memory_confirmation_service import confirm, get_status
from backend.tests import factories

# ════════════════════════════════════════════════════════════════════
# Stale detection — funções puras
# ════════════════════════════════════════════════════════════════════


def test_is_stale_by_age_recent_is_not_stale():
    confirmed_at = datetime.now(timezone.utc) - timedelta(days=30)
    assert is_stale_by_age(confirmed_at) is False


def test_is_stale_by_age_over_year_is_stale():
    confirmed_at = datetime.now(timezone.utc) - timedelta(days=400)
    assert is_stale_by_age(confirmed_at) is True


def test_is_stale_by_age_respects_custom_threshold():
    confirmed_at = datetime.now(timezone.utc) - timedelta(days=10)
    assert is_stale_by_age(confirmed_at, max_age_days=5) is True
    assert is_stale_by_age(confirmed_at, max_age_days=30) is False


def test_is_stale_by_value_numeric_below_threshold_not_stale():
    # 1% diff < 2% threshold
    assert is_stale_by_value("7450.00", "7524.50") is False


def test_is_stale_by_value_numeric_above_threshold_is_stale():
    # 5% diff ≥ 2%
    assert is_stale_by_value("7450.00", "7822.50") is True


def test_is_stale_by_value_categorical_any_diff_is_stale():
    assert is_stale_by_value("simples_nacional", "lucro_presumido") is True


def test_is_stale_by_value_equal_not_stale():
    assert is_stale_by_value("foo", "foo") is False


def test_is_stale_by_value_missing_snapshot_is_stale():
    assert is_stale_by_value(None, "anything") is True


def test_is_stale_by_value_zero_snapshot_with_nonzero_current_is_stale():
    assert is_stale_by_value("0", "100") is True
    assert is_stale_by_value("0", "0") is False


# ════════════════════════════════════════════════════════════════════
# Repository — CRUD (DB)
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_repo_create_persists(db):
    user = await factories.make_user(db)
    ws = await factories.make_workspace(db, owner=user)
    repo = WorkspaceMemoryConfirmationRepository(db)
    row = await repo.create(
        ws.id,
        "e5.patrimonio.liquido",
        "e5",
        confirmed_value_snapshot="1500000.00",
        confirmed_by_user_id=user.id,
        note="revisado em 2026-05-23",
    )
    await db.commit()
    assert row.id is not None
    assert row.memory_key == "e5.patrimonio.liquido"  # gitleaks:allow (memory_key, não secret)
    assert row.source_aggregate == "e5"
    assert row.confirmed_value_snapshot == "1500000.00"
    assert row.confirmed_by_user_id == user.id


async def _seed_two_confirmations(db, ws_id, user_id, key, source, vals_days_ago):
    repo = WorkspaceMemoryConfirmationRepository(db)
    for snap, days_ago in vals_days_ago:
        await repo.create(
            ws_id,
            key,
            source,
            confirmed_value_snapshot=snap,
            confirmed_by_user_id=user_id,
            confirmed_at=datetime.now(timezone.utc) - timedelta(days=days_ago),
        )
    await db.commit()
    return repo


@pytest.mark.asyncio
async def test_repo_get_latest_returns_most_recent(db):
    user = await factories.make_user(db)
    ws = await factories.make_workspace(db, owner=user)
    repo = await _seed_two_confirmations(
        db,
        ws.id,
        user.id,
        "irpf_metadata.regime_dominante",
        "irpf_metadata",
        [("simples_nacional", 10), ("lucro_presumido", 0)],
    )
    latest = await repo.get_latest(ws.id, "irpf_metadata.regime_dominante")
    assert latest is not None
    assert latest.confirmed_value_snapshot == "lucro_presumido"


@pytest.mark.asyncio
async def test_repo_append_only_history_preserved(db):
    user = await factories.make_user(db)
    ws = await factories.make_workspace(db, owner=user)
    repo = WorkspaceMemoryConfirmationRepository(db)

    for snap, days_ago in [("1000", 30), ("1500", 20), ("2000", 10)]:
        await repo.create(
            ws.id,
            "e5.aporte_mensal",
            "e5",
            confirmed_value_snapshot=snap,
            confirmed_by_user_id=user.id,
            confirmed_at=datetime.now(timezone.utc) - timedelta(days=days_ago),
        )
    await db.commit()

    history = await repo.list_history(ws.id, "e5.aporte_mensal")
    assert len(history) == 3
    assert [h.confirmed_value_snapshot for h in history] == ["2000", "1500", "1000"]


@pytest.mark.asyncio
async def test_repo_tenant_isolation(db):
    user_a = await factories.make_user(db)
    ws_a = await factories.make_workspace(db, owner=user_a)
    user_b = await factories.make_user(db)
    ws_b = await factories.make_workspace(db, owner=user_b)
    repo = WorkspaceMemoryConfirmationRepository(db)
    await repo.create(ws_a.id, "e5.foo", "e5", confirmed_value_snapshot="A")
    await repo.create(ws_b.id, "e5.foo", "e5", confirmed_value_snapshot="B")
    await db.commit()

    a = await repo.get_latest(ws_a.id, "e5.foo")
    b = await repo.get_latest(ws_b.id, "e5.foo")
    assert a is not None and a.confirmed_value_snapshot == "A"
    assert b is not None and b.confirmed_value_snapshot == "B"


# ════════════════════════════════════════════════════════════════════
# Service — confirm + get_status
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_service_confirm_returns_row(db):
    user = await factories.make_user(db)
    ws = await factories.make_workspace(db, owner=user)
    row = await confirm(
        ws.id,
        "e5.patrimonio.liquido",
        "e5",
        db=db,
        user_id=user.id,
        snapshot="1500000.00",
    )
    await db.commit()
    assert isinstance(row, WorkspaceMemoryConfirmation)
    assert row.confirmed_by_user_id == user.id


@pytest.mark.asyncio
async def test_service_get_status_when_not_confirmed(db):
    user = await factories.make_user(db)
    ws = await factories.make_workspace(db, owner=user)
    status = await get_status(ws.id, "e5.unknown_key", current_value=None, db=db)
    assert status.confirmed is False
    assert status.confirmed_at is None
    assert status.stale is False
    assert status.stale_reason is None


@pytest.mark.asyncio
async def test_service_get_status_recent_value_stable_is_confirmed(db):
    user = await factories.make_user(db)
    ws = await factories.make_workspace(db, owner=user)
    await confirm(
        ws.id,
        "e5.patrimonio.liquido",
        "e5",
        db=db,
        user_id=user.id,
        snapshot="1500000.00",
    )
    await db.commit()

    status = await get_status(ws.id, "e5.patrimonio.liquido", "1505000.00", db=db)
    assert status.confirmed is True
    assert status.stale is False
    assert status.confirmed_by_user_id == user.id


@pytest.mark.asyncio
async def test_service_get_status_stale_by_value(db):
    user = await factories.make_user(db)
    ws = await factories.make_workspace(db, owner=user)
    await confirm(
        ws.id,
        "e5.aporte_mensal",
        "e5",
        db=db,
        user_id=user.id,
        snapshot="7450.00",
    )
    await db.commit()

    status = await get_status(ws.id, "e5.aporte_mensal", "7822.50", db=db)
    assert status.confirmed is False
    assert status.stale is True
    assert status.stale_reason == "value"


@pytest.mark.asyncio
async def test_service_get_status_stale_by_age(db):
    user = await factories.make_user(db)
    ws = await factories.make_workspace(db, owner=user)
    repo = WorkspaceMemoryConfirmationRepository(db)
    old = datetime.now(timezone.utc) - timedelta(days=400)
    await repo.create(
        ws.id,
        "e5.patrimonio.liquido",
        "e5",
        confirmed_value_snapshot="1500000.00",
        confirmed_by_user_id=user.id,
        confirmed_at=old,
    )
    await db.commit()

    status = await get_status(ws.id, "e5.patrimonio.liquido", "1500000.00", db=db)
    assert status.confirmed is False
    assert status.stale is True
    assert status.stale_reason == "age"
