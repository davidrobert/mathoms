"""Tests for auth endpoints — register, login, me."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    resp = await client.post("/api/auth/register", json={
        "email": "new@test.com",
        "password": "senha123",
        "full_name": "New User",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    payload = {
        "email": "dup@test.com",
        "password": "senha123",
        "full_name": "First User",
    }
    resp1 = await client.post("/api/auth/register", json=payload)
    assert resp1.status_code == 201

    resp2 = await client.post("/api/auth/register", json=payload)
    assert resp2.status_code == 409


@pytest.mark.asyncio
async def test_register_invalid_email(client: AsyncClient):
    resp = await client.post("/api/auth/register", json={
        "email": "not-an-email",
        "password": "senha123",
        "full_name": "Bad Email",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    await client.post("/api/auth/register", json={
        "email": "login@test.com",
        "password": "senha123",
        "full_name": "Login User",
    })
    resp = await client.post("/api/auth/login", json={
        "email": "login@test.com",
        "password": "senha123",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    await client.post("/api/auth/register", json={
        "email": "wrongpw@test.com",
        "password": "correct",
        "full_name": "Wrong PW",
    })
    resp = await client.post("/api/auth/login", json={
        "email": "wrongpw@test.com",
        "password": "incorrect",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient):
    resp = await client.post("/api/auth/login", json={
        "email": "noone@test.com",
        "password": "anything",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_authenticated(auth_client: AsyncClient):
    resp = await auth_client.get("/api/auth/me")
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "fixture@test.com"
    assert data["full_name"] == "Fixture User"
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_me_no_token(client: AsyncClient):
    resp = await client.get("/api/auth/me")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_me_invalid_token(client: AsyncClient):
    resp = await client.get("/api/auth/me", headers={
        "Authorization": "Bearer invalid.token.here",
    })
    assert resp.status_code == 401
