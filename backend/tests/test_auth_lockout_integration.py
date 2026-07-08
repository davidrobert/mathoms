"""Integration tests do brute-force lockout em /auth/login (7B.13)."""

# Substitui ``get_default_lockout_service`` por ``InMemoryBruteForceLockoutBackend``
# para validar a integração ponta-a-ponta sem Redis.

from __future__ import annotations

import importlib

import pytest
from httpx import AsyncClient

from backend.app.services.security.brute_force_lockout import (
    BruteForceLockoutService,
    InMemoryBruteForceLockoutBackend,
)

login_module = importlib.import_module("backend.app.application.auth.login_user")


@pytest.fixture
def lockout_backend() -> InMemoryBruteForceLockoutBackend:
    return InMemoryBruteForceLockoutBackend()


@pytest.fixture(autouse=True)
def patch_lockout_service(monkeypatch, lockout_backend: InMemoryBruteForceLockoutBackend):
    """Substitui o resolver default por InMemory backend determinístico."""
    service = BruteForceLockoutService(
        lockout_backend,
        threshold=5,
        durations_s=(60, 300, 900, 3600),
    )
    monkeypatch.setattr(
        login_module,
        "get_default_lockout_service",
        lambda: service,
    )
    return service


async def _register(client: AsyncClient, email: str, password: str = "senha123") -> None:
    resp = await client.post(
        "/api/auth/register",
        json={"email": email, "password": password, "full_name": "Test"},
    )
    assert resp.status_code == 201, resp.text


async def _login(client: AsyncClient, email: str, password: str):
    return await client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
    )


class TestLockoutFlow:
    @pytest.mark.asyncio
    async def test_4_wrong_passwords_still_returns_401(self, client: AsyncClient) -> None:
        email = "lockout1@test.com"
        await _register(client, email)
        for _ in range(4):
            resp = await _login(client, email, "wrong")
            assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_5th_wrong_password_locks_with_429(self, client: AsyncClient) -> None:
        email = "lockout2@test.com"
        await _register(client, email)
        for _ in range(4):
            await _login(client, email, "wrong")
        resp = await _login(client, email, "wrong")
        assert resp.status_code == 429
        assert resp.headers.get("Retry-After") == "60"
        body = resp.json()
        assert body["detail"]["code"] == "account_locked"
        assert "60" in body["detail"]["message"]

    @pytest.mark.asyncio
    async def test_6th_attempt_with_correct_password_still_blocked(
        self, client: AsyncClient
    ) -> None:
        email = "lockout3@test.com"
        await _register(client, email, password="senha123")
        for _ in range(5):
            await _login(client, email, "wrong")
        # Mesmo com senha certa, está travado
        resp = await _login(client, email, "senha123")
        assert resp.status_code == 429

    @pytest.mark.asyncio
    async def test_lockout_expires_and_login_succeeds(
        self,
        client: AsyncClient,
        lockout_backend: InMemoryBruteForceLockoutBackend,
    ) -> None:
        email = "lockout4@test.com"
        await _register(client, email, password="senha123")
        for _ in range(5):
            await _login(client, email, "wrong")
        # Avança o relógio do backend além da duração do lock
        lockout_backend.advance_clock(61.0)
        resp = await _login(client, email, "senha123")
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    @pytest.mark.asyncio
    async def test_correct_password_resets_counter(self, client: AsyncClient) -> None:
        email = "lockout5@test.com"
        await _register(client, email, password="senha123")
        # 4 falhas, depois 1 sucesso → contador zera
        for _ in range(4):
            await _login(client, email, "wrong")
        ok = await _login(client, email, "senha123")
        assert ok.status_code == 200
        # Mais 4 falhas — não deve travar (contador foi a 0)
        for _ in range(4):
            resp = await _login(client, email, "wrong")
            assert resp.status_code == 401


class TestLockoutPerEmail:
    @pytest.mark.asyncio
    async def test_lockout_does_not_leak_between_users(self, client: AsyncClient) -> None:
        await _register(client, "victim@test.com", password="senha123")
        await _register(client, "spectator@test.com", password="senha123")

        for _ in range(5):
            await _login(client, "victim@test.com", "wrong")

        # spectator continua livre
        ok = await _login(client, "spectator@test.com", "senha123")
        assert ok.status_code == 200


class TestNonexistentEmail:
    @pytest.mark.asyncio
    async def test_lockout_tracks_unknown_emails_too(self, client: AsyncClient) -> None:
        """Defesa anti-enumeração: e-mail inexistente conta como falha."""
        for _ in range(4):
            resp = await _login(client, "ghost@test.com", "anything")
            assert resp.status_code == 401
        resp = await _login(client, "ghost@test.com", "anything")
        assert resp.status_code == 429
