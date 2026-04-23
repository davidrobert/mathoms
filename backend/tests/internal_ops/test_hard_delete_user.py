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
async def test_hard_delete_removes_row(db, audit_path: Path) -> None:
    user = await make_user(db)
    await db.commit()

    result = await hard_delete_user(db, user.id, actor="ops1", reason="LGPD request #42")
    await db.commit()

    assert result.ok
    assert (await db.execute(select(User).where(User.id == user.id))).scalar_one_or_none() is None

    entry = read_audit(path=audit_path)[0]
    assert entry["action"] == "user.hard_delete"
    assert entry["details"]["reason"] == "LGPD request #42"


@pytest.mark.asyncio
async def test_hard_delete_requires_reason(db, audit_path: Path) -> None:
    user = await make_user(db)
    await db.commit()

    result = await hard_delete_user(db, user.id, actor="ops1", reason="  ")
    assert not result.ok
    assert result.error == "reason_required"
    assert read_audit(path=audit_path) == []


@pytest.mark.asyncio
async def test_hard_delete_missing_user(db, audit_path: Path) -> None:
    result = await hard_delete_user(
        db, "00000000-0000-0000-0000-000000000000", actor="ops1", reason="test"
    )
    assert not result.ok
    assert result.error == "user_not_found"
