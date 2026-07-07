"""Testes de mutações de user (email/flag dev/profile)."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import select

from backend.app.models.user import User
from backend.app.services.internal_ops.audit import read_audit
from backend.app.services.internal_ops.set_developer_flag import set_developer_flag
from backend.app.services.internal_ops.update_user_email import update_user_email
from backend.app.services.internal_ops.update_user_profile import update_user_profile
from backend.tests.factories import make_user


@pytest.mark.asyncio
async def test_set_developer_flag_bumps_token_version(db) -> None:
    user = await make_user(db)
    prev_tv = user.token_version
    await db.commit()

    result = await set_developer_flag(db, user.id, enabled=True, actor="ops1")
    await db.commit()

    assert result.ok and result.details["changed"] is True
    refreshed = (await db.execute(select(User).where(User.id == user.id))).scalar_one()
    assert refreshed.is_developer is True
    assert refreshed.token_version == prev_tv + 1


@pytest.mark.asyncio
async def test_set_developer_flag_noop_when_same(db) -> None:
    user = await make_user(db)
    await db.commit()
    result = await set_developer_flag(db, user.id, enabled=False, actor="ops1")
    assert result.details["changed"] is False
    assert await read_audit(db) == []


@pytest.mark.asyncio
async def test_update_email_bumps_token_version(db) -> None:
    user = await make_user(db, email="old@test.com")
    prev_tv = user.token_version
    await db.commit()

    result = await update_user_email(db, user.id, new_email="New@Test.com", actor="ops1")
    await db.commit()

    assert result.ok and result.details["email"] == "new@test.com"
    refreshed = (await db.execute(select(User).where(User.id == user.id))).scalar_one()
    assert refreshed.email == "new@test.com"
    assert refreshed.token_version == prev_tv + 1


@pytest.mark.asyncio
async def test_update_email_collision(db) -> None:
    a = await make_user(db, email="a@test.com")
    b = await make_user(db, email="b@test.com")
    await db.commit()

    result = await update_user_email(db, b.id, new_email="a@test.com", actor="ops1")
    assert not result.ok and result.error == "email_taken"

    refreshed = (await db.execute(select(User).where(User.id == b.id))).scalar_one()
    assert refreshed.email == "b@test.com"
    assert a.id != b.id


@pytest.mark.asyncio
async def test_update_email_invalid(db) -> None:
    user = await make_user(db)
    await db.commit()
    result = await update_user_email(db, user.id, new_email="no-at-sign", actor="ops1")
    assert not result.ok and result.error == "invalid_email"


@pytest.mark.asyncio
async def test_update_email_idempotent(db) -> None:
    user = await make_user(db, email="same@test.com")
    prev_tv = user.token_version
    await db.commit()
    result = await update_user_email(db, user.id, new_email="same@test.com", actor="ops1")
    assert result.ok and result.details["changed"] is False
    refreshed = (await db.execute(select(User).where(User.id == user.id))).scalar_one()
    assert refreshed.token_version == prev_tv


@pytest.mark.asyncio
async def test_update_profile_partial(db) -> None:
    user = await make_user(db, full_name="Old Name")
    await db.commit()

    result = await update_user_profile(
        db, user.id, actor="ops1", full_name="New Name", is_active=False
    )
    await db.commit()
    assert result.ok and result.details["changed"] is True
    refreshed = (await db.execute(select(User).where(User.id == user.id))).scalar_one()
    assert refreshed.full_name == "New Name"
    assert refreshed.is_active is False


@pytest.mark.asyncio
async def test_update_profile_no_fields(db) -> None:
    user = await make_user(db)
    await db.commit()
    result = await update_user_profile(db, user.id, actor="ops1")
    assert result.ok and result.details["changed"] is False
    assert await read_audit(db) == []
