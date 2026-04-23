"""Testa o gate `INTERNAL_OPS_UI_ENABLED` e isolamento de auth."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_admin_returns_404_when_disabled(client) -> None:
    from backend.app.core.config import settings

    # Flag default é False — rota retorna 404 mesmo sem cookie.
    assert settings.INTERNAL_OPS_UI_ENABLED is False
    resp = await client.post("/admin/login", json={"username": "x", "password": "y"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_admin_401_without_cookie(admin_ui_enabled, ops_yaml, client) -> None:
    resp = await client.get("/admin/users")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_admin_401_with_invalid_cookie(admin_ui_enabled, ops_yaml, client) -> None:
    client.cookies.set("ops_session", "garbage.token", domain="test", path="/admin")
    resp = await client.get("/admin/users")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_client_jwt_not_accepted_by_admin(
    admin_ui_enabled, ops_yaml, auth_client
) -> None:
    """Token do JWT cliente (SECRET_KEY) não entra no /admin/*."""
    auth = auth_client.headers.get("Authorization")
    assert auth
    # Usa client novo para não herdar o cookie do auth_client
    from httpx import ASGITransport, AsyncClient

    from backend.app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/admin/users", headers={"Authorization": auth})
    assert resp.status_code == 401
