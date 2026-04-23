"""Testes de reset_password."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import select

from backend.app.core.security import verify_password
from backend.app.models.user import User
from backend.app.services.internal_ops.audit import read_audit
from backend.app.services.internal_ops.reset_password import (
    generate_temp_password,
    reset_password,
)
from backend.tests.factories import make_user


@pytest.mark.asyncio
async def test_reset_generates_password(db, audit_path: Path) -> None:
    user = await make_user(db, password="OldPw!")
    prev_tv = user.token_version
    await db.commit()

    result = await reset_password(db, user.id, actor="ops1")
    await db.commit()

    assert result.ok
    temp = result.details["temp_password"]
    assert isinstance(temp, str) and len(temp) == 16

    refreshed = (await db.execute(select(User).where(User.id == user.id))).scalar_one()
    assert verify_password(temp, refreshed.hashed_password)
    assert not verify_password("OldPw!", refreshed.hashed_password)
    assert refreshed.token_version == prev_tv + 1

    entry = read_audit(path=audit_path)[0]
    assert entry["action"] == "user.reset_password"
    assert "password" not in entry["details"]


@pytest.mark.asyncio
async def test_reset_invalidates_existing_jwt(db, audit_path: Path) -> None:
    """Token emitido antes do reset deve falhar o check de `tv` em deps.get_current_user."""
    from fastapi import HTTPException
    from fastapi.security import HTTPAuthorizationCredentials

    from backend.app.core.deps import get_current_user
    from backend.app.core.security import create_access_token

    user = await make_user(db, password="OldPw!")
    await db.commit()
    old_token = create_access_token(subject=user.id, token_version=user.token_version)

    await reset_password(db, user.id, actor="ops1")
    await db.commit()

    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=old_token)
    with pytest.raises(HTTPException) as exc:
        await get_current_user(credentials=creds, db=db)
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_reset_explicit_password(db, audit_path: Path) -> None:
    user = await make_user(db)
    await db.commit()

    result = await reset_password(db, user.id, actor="ops1", new_password="Explicit123!")
    await db.commit()

    assert result.details["temp_password"] == "Explicit123!"
    refreshed = (await db.execute(select(User).where(User.id == user.id))).scalar_one()
    assert verify_password("Explicit123!", refreshed.hashed_password)


@pytest.mark.asyncio
async def test_reset_missing_user(db, audit_path: Path) -> None:
    result = await reset_password(db, "nope", actor="ops1")
    assert not result.ok and result.error == "user_not_found"


def test_generate_temp_password_length() -> None:
    assert len(generate_temp_password()) == 16
    assert len(generate_temp_password(length=24)) == 24
