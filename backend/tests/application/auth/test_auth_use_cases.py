"""Use cases ``register_user`` / ``login_user`` (A6e.4 · ADR-072)."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from backend.app.application.auth import login_user, register_user
from backend.app.application.base import AuthenticationError, ConflictError
from backend.app.models.user import User
from backend.app.models.workspace_member import WorkspaceMember
from backend.app.schemas.auth import LoginRequest, RegisterRequest


@pytest.mark.asyncio
async def test_register_creates_user_workspace_and_owner_membership(db):
    resp = await register_user(
        RegisterRequest(
            email="novo@test.com",
            password="senha123",
            full_name="Novo User",
        ),
        db=db,
    )
    assert resp.access_token

    user = (await db.execute(select(User).where(User.email == "novo@test.com"))).scalar_one()
    members = (
        (await db.execute(select(WorkspaceMember).where(WorkspaceMember.user_id == user.id)))
        .scalars()
        .all()
    )
    assert len(members) == 1
    assert members[0].role == "owner"


@pytest.mark.asyncio
async def test_register_duplicate_email_raises_conflict(db):
    body = RegisterRequest(email="dup@test.com", password="senha123", full_name="Dup")
    await register_user(body, db=db)
    with pytest.raises(ConflictError):
        await register_user(body, db=db)


@pytest.mark.asyncio
async def test_login_valid_credentials_returns_token(db):
    await register_user(
        RegisterRequest(email="login@test.com", password="senha123", full_name="Login"),
        db=db,
    )
    resp = await login_user(LoginRequest(email="login@test.com", password="senha123"), db=db)
    assert resp.access_token


@pytest.mark.asyncio
async def test_login_wrong_password_raises_authentication_error(db):
    await register_user(
        RegisterRequest(email="wp@test.com", password="certa", full_name="WP"),
        db=db,
    )
    with pytest.raises(AuthenticationError):
        await login_user(LoginRequest(email="wp@test.com", password="errada"), db=db)


@pytest.mark.asyncio
async def test_login_unknown_email_raises_authentication_error(db):
    with pytest.raises(AuthenticationError):
        await login_user(LoginRequest(email="none@test.com", password="x"), db=db)
