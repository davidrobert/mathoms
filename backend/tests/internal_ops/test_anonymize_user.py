"""Testes de anonymize_user (ADR-116)."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import select

from backend.app.core.security import verify_password
from backend.app.models.user import User
from backend.app.models.workspace import Workspace
from backend.app.services.internal_ops.anonymize_user import anonymize_user
from backend.app.services.internal_ops.audit import read_audit
from backend.tests.factories import make_user, make_workspace


@pytest.mark.asyncio
async def test_anonymize_preserves_user_id_and_fks(db, audit_path: Path) -> None:
    user = await make_user(db, email="before@test.com", password="OldPw123!")
    ws = await make_workspace(db, owner=user)
    await db.commit()

    original_id = user.id

    result = await anonymize_user(db, user.id, actor="ops1")
    await db.commit()

    assert result.ok
    assert result.details["user_id"] == original_id

    refreshed = (await db.execute(select(User).where(User.id == original_id))).scalar_one()
    assert refreshed.email.endswith("@anonymized.invalid")
    assert refreshed.full_name == "Usuário anonimizado"
    assert refreshed.is_active is False
    assert refreshed.token_version >= 1
    assert not verify_password("OldPw123!", refreshed.hashed_password)

    ws_refreshed = (await db.execute(select(Workspace).where(Workspace.id == ws.id))).scalar_one()
    assert ws_refreshed.owner_id == original_id


@pytest.mark.asyncio
async def test_anonymize_writes_audit(db, audit_path: Path) -> None:
    user = await make_user(db)
    await db.commit()

    await anonymize_user(db, user.id, actor="ops1")
    await db.commit()

    entries = read_audit(path=audit_path)
    assert len(entries) == 1
    assert entries[0]["action"] == "user.anonymize"
    assert entries[0]["actor"] == "ops1"
    assert entries[0]["target_id"] == user.id


@pytest.mark.asyncio
async def test_anonymize_missing_user(db, audit_path: Path) -> None:
    result = await anonymize_user(db, "00000000-0000-0000-0000-000000000000", actor="ops1")
    assert not result.ok
    assert result.error == "user_not_found"
    assert read_audit(path=audit_path) == []


@pytest.mark.asyncio
async def test_anonymize_idempotent(db, audit_path: Path) -> None:
    user = await make_user(db)
    await db.commit()

    first = await anonymize_user(db, user.id, actor="ops1")
    await db.commit()
    second = await anonymize_user(db, user.id, actor="ops1")
    await db.commit()

    assert first.ok and second.ok
    assert first.details["anonymized_email"] == second.details["anonymized_email"]
    entries = read_audit(path=audit_path)
    assert entries[1]["details"]["already_anonymized"] is True
