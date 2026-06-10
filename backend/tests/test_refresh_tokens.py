"""ADR-170 (W3-T03) — refresh tokens: rotação, reuse, grace window, logout,
flag. Cookie path é ``/api/v1/auth`` — testes usam o prefixo canônico (o
alias legado ``/api/auth`` não recebe o cookie por design)."""

from datetime import datetime, timedelta, timezone

import jwt
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from backend.app.core.config import settings
from backend.app.models.refresh_token_family import RefreshTokenFamily
from backend.app.models.user import User

LOGIN = "/api/v1/auth/login"
REGISTER = "/api/v1/auth/register"
REFRESH = "/api/v1/auth/refresh"
LOGOUT = "/api/v1/auth/logout"
REFRESH_HEADERS = {"X-Refresh-Request": "1"}

CREDS = {"email": "refresh@test.com", "password": "senha123"}


@pytest.fixture
def refresh_flow(monkeypatch):
    """Liga o flow + Secure=False (httpx jar descarta cookie Secure em http://test)."""
    monkeypatch.setattr(settings, "AUTH_REFRESH_FLOW", True)
    monkeypatch.setattr(settings, "AUTH_COOKIE_SECURE", False)
    return settings


async def _refresh_with(client: AsyncClient, cookie_value: str):
    """POST /auth/refresh com cookie explícito — o jar do httpx não transmite
    cookies setados manualmente (domain/path matching), então o header Cookie
    vai direto e o jar é limpo antes para não duplicar."""
    client.cookies.clear()
    return await client.post(
        REFRESH, headers={**REFRESH_HEADERS, "Cookie": f"fin_refresh={cookie_value}"}
    )


async def _register_and_login(client: AsyncClient) -> str:
    await client.post(REGISTER, json={**CREDS, "full_name": "Refresh User"})
    resp = await client.post(LOGIN, json=CREDS)
    assert resp.status_code == 200
    return resp.json()["access_token"]


# ── Flag off (default) — comportamento ADR-057 legado intacto ──────────────


@pytest.mark.asyncio
async def test_flag_off_login_sets_no_cookie_and_refresh_404(client: AsyncClient):
    await _register_and_login(client)
    assert "fin_refresh" not in client.cookies
    resp = await client.post(REFRESH, headers=REFRESH_HEADERS)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_flag_off_access_token_keeps_24h_ttl(client: AsyncClient):
    token = await _register_and_login(client)
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    ttl = datetime.fromtimestamp(payload["exp"], tz=timezone.utc) - datetime.now(timezone.utc)
    assert ttl > timedelta(hours=23)


# ── Flag on — emissão e atributos do cookie ────────────────────────────────


@pytest.mark.asyncio
async def test_login_sets_httponly_cookie_with_restricted_path(client: AsyncClient, refresh_flow):
    await _register_and_login(client)
    set_cookie = ""
    resp = await client.post(LOGIN, json=CREDS)
    set_cookie = resp.headers["set-cookie"]
    assert "fin_refresh=" in set_cookie
    assert "HttpOnly" in set_cookie
    assert "Path=/api/v1/auth" in set_cookie
    assert "samesite=lax" in set_cookie.lower()


@pytest.mark.asyncio
async def test_cookie_secure_attr_follows_setting(client: AsyncClient, refresh_flow, monkeypatch):
    monkeypatch.setattr(settings, "AUTH_COOKIE_SECURE", True)
    await client.post(REGISTER, json={**CREDS, "full_name": "Refresh User"})
    resp = await client.post(LOGIN, json=CREDS)
    assert "Secure" in resp.headers["set-cookie"]


@pytest.mark.asyncio
async def test_flag_on_access_token_has_15min_ttl(client: AsyncClient, refresh_flow):
    token = await _register_and_login(client)
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    ttl = datetime.fromtimestamp(payload["exp"], tz=timezone.utc) - datetime.now(timezone.utc)
    assert timedelta(minutes=14) < ttl <= timedelta(minutes=15)


@pytest.mark.asyncio
async def test_jwt_payload_contract_unchanged_with_flag_on(client: AsyncClient, refresh_flow):
    """Emenda ADR-170: payload permanece {sub, exp, tv} (contrato ADR-109)."""
    token = await _register_and_login(client)
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    assert set(payload.keys()) == {"sub", "exp", "tv"}


# ── Rotação ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_refresh_rotates_cookie_and_issues_access(client: AsyncClient, refresh_flow):
    await _register_and_login(client)
    old_cookie = client.cookies["fin_refresh"]
    resp = await client.post(REFRESH, headers=REFRESH_HEADERS)
    assert resp.status_code == 200
    assert resp.json()["access_token"]
    assert resp.headers["cache-control"] == "no-store"
    assert client.cookies["fin_refresh"] != old_cookie


@pytest.mark.asyncio
async def test_refresh_requires_csrf_header(client: AsyncClient, refresh_flow):
    await _register_and_login(client)
    resp = await client.post(REFRESH)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_refresh_without_cookie_is_401(client: AsyncClient, refresh_flow):
    resp = await client.post(REFRESH, headers=REFRESH_HEADERS)
    assert resp.status_code == 401


# ── Reuse detection + grace window ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_reuse_within_grace_window_does_not_revoke(client: AsyncClient, refresh_flow):
    await _register_and_login(client)
    stolen = client.cookies["fin_refresh"]
    resp1 = await client.post(REFRESH, headers=REFRESH_HEADERS)
    assert resp1.status_code == 200
    current = client.cookies["fin_refresh"]

    # 2ª tab apresenta o secret anterior dentro da janela → access OK, sem
    # nova rotação (cookie do jar permanece o vigente).
    resp2 = await _refresh_with(client, stolen)
    assert resp2.status_code == 200
    assert "set-cookie" not in resp2.headers

    resp3 = await _refresh_with(client, current)
    assert resp3.status_code == 200


@pytest.mark.asyncio
async def test_reuse_outside_grace_revokes_family(client: AsyncClient, refresh_flow, monkeypatch):
    monkeypatch.setattr(settings, "AUTH_REFRESH_GRACE_WINDOW_S", 0)
    await _register_and_login(client)
    stolen = client.cookies["fin_refresh"]
    resp1 = await client.post(REFRESH, headers=REFRESH_HEADERS)
    assert resp1.status_code == 200
    current = client.cookies["fin_refresh"]

    resp2 = await _refresh_with(client, stolen)
    assert resp2.status_code == 401

    # Família inteira revogada — o token "legítimo" também morre.
    resp3 = await _refresh_with(client, current)
    assert resp3.status_code == 401


@pytest.mark.asyncio
async def test_unknown_secret_with_valid_family_revokes(client: AsyncClient, refresh_flow, db):
    await _register_and_login(client)
    family_id = client.cookies["fin_refresh"].split(".")[0]
    resp = await _refresh_with(client, f"{family_id}.totally-forged-secret")
    assert resp.status_code == 401

    # Reuse real revoga: o secret legítimo da mesma família também morre.
    result = await db.execute(select(RefreshTokenFamily).where(RefreshTokenFamily.id == family_id))
    assert result.scalar_one().revoked_at is not None


# ── Forced logout (tv bump) + logout ───────────────────────────────────────


@pytest.mark.asyncio
async def test_token_version_bump_kills_refresh_family(client: AsyncClient, refresh_flow, db):
    await _register_and_login(client)
    family_id = client.cookies["fin_refresh"].split(".")[0]
    result = await db.execute(select(User).where(User.email == CREDS["email"]))
    user = result.scalar_one()
    user.token_version += 1
    await db.commit()

    resp = await client.post(REFRESH, headers=REFRESH_HEADERS)
    assert resp.status_code == 401

    result = await db.execute(select(RefreshTokenFamily).where(RefreshTokenFamily.id == family_id))
    assert result.scalar_one().revoked_at is not None


@pytest.mark.asyncio
async def test_logout_revokes_family_and_clears_cookie(client: AsyncClient, refresh_flow):
    await _register_and_login(client)
    cookie_before = client.cookies["fin_refresh"]
    resp = await client.post(LOGOUT)
    assert resp.status_code == 204
    assert "fin_refresh" not in client.cookies  # delete_cookie limpou o jar

    # Replay do cookie pré-logout prova a revogação no servidor.
    resp2 = await _refresh_with(client, cookie_before)
    assert resp2.status_code == 401


@pytest.mark.asyncio
async def test_logout_without_cookie_is_idempotent(client: AsyncClient):
    resp = await client.post(LOGOUT)
    assert resp.status_code == 204
