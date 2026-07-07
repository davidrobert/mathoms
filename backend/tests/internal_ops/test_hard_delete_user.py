"""Testes de hard_delete_user (ADR-116)."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import select

from backend.app.models.user import User
from backend.app.services.internal_ops.audit import read_audit
from backend.app.services.internal_ops.hard_delete_user import hard_delete_user
from backend.tests.factories import make_user


@pytest.mark.asyncio
async def test_hard_delete_removes_row(db) -> None:
    user = await make_user(db)
    await db.commit()

    result = await hard_delete_user(db, user.id, actor="ops1", reason="LGPD request #42")
    await db.commit()

    assert result.ok
    assert (await db.execute(select(User).where(User.id == user.id))).scalar_one_or_none() is None

    entry = (await read_audit(db))[0]
    assert entry["action"] == "user.hard_delete"
    assert entry["details"]["reason"] == "LGPD request #42"


@pytest.mark.asyncio
async def test_hard_delete_requires_reason(db) -> None:
    user = await make_user(db)
    await db.commit()

    result = await hard_delete_user(db, user.id, actor="ops1", reason="  ")
    assert not result.ok
    assert result.error == "reason_required"
    assert await read_audit(db) == []


@pytest.mark.asyncio
async def test_hard_delete_missing_user(db) -> None:
    result = await hard_delete_user(
        db, "00000000-0000-0000-0000-000000000000", actor="ops1", reason="test"
    )
    assert not result.ok
    assert result.error == "user_not_found"
