"""Testes de /admin/login, /admin/logout, /admin/me."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_login_success_sets_httponly_cookie(
    admin_ui_enabled, ops_yaml, audit_path, client
) -> None:
    resp = await client.post(
        "/admin/login", json={"username": "alice", "password": "AliceSuper!Pw1"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["username"] == "alice"
    assert body["role"] == "superadmin"

    set_cookie = resp.headers.get("set-cookie", "")
    lowered = set_cookie.lower()
    assert "ops_session=" in lowered
    assert "httponly" in lowered
    assert "samesite=strict" in lowered
    assert "path=/admin" in lowered


@pytest.mark.asyncio
async def test_login_wrong_password(admin_ui_enabled, ops_yaml, audit_path, client) -> None:
    resp = await client.post(
        "/admin/login", json={"username": "alice", "password": "wrong"}
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_user(admin_ui_enabled, ops_yaml, audit_path, client) -> None:
    resp = await client.post(
        "/admin/login", json={"username": "ghost", "password": "x"}
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_returns_principal(
    ops_session_token_superadmin, admin_ui_enabled, ops_yaml, client
) -> None:
    client.cookies.set(
        "ops_session", ops_session_token_superadmin, domain="test", path="/admin"
    )
    resp = await client.get("/admin/me")
    assert resp.status_code == 200
    assert resp.json() == {"username": "alice", "role": "superadmin"}


@pytest.mark.asyncio
async def test_logout_clears_cookie(
    ops_session_token_superadmin, admin_ui_enabled, ops_yaml, client
) -> None:
    client.cookies.set(
        "ops_session", ops_session_token_superadmin, domain="test", path="/admin"
    )
    resp = await client.post("/admin/logout")
    assert resp.status_code == 200
    # O Set-Cookie de logout remove o cookie (Max-Age=0).
    assert "ops_session=" in resp.headers.get("set-cookie", "")
