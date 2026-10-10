"""O IP do cliente é o hop que o proxy confiável acrescentou, não o que o cliente escreveu.

Regressão: o ``X-Forwarded-For`` era lido pelo hop mais à esquerda, que o
cliente controla. Bastava rotacionar um primeiro hop forjado a cada request
para nunca encher o balde per-IP do login — credential stuffing cross-account
sem throttle (o lockout per-conta não alcança quem troca de conta a cada tiro).
"""

from __future__ import annotations

import re
from collections.abc import AsyncIterator
from pathlib import Path

import fakeredis
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError
from starlette.requests import Request
from starlette.types import Scope
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

import backend.app.services.security.rate_limit as rl
import backend.app.services.security.register_rate_limit as register_rl
from backend.app.core.config import Settings, settings
from backend.app.main import app
from backend.app.services.audit import client_meta

_REPO_ROOT = Path(__file__).resolve().parents[2]
_LAUNCHERS = ("backend/scripts/entrypoint.sh", "dev/entrypoint.dev.sh", "Makefile")
_APP_LAUNCH = "uvicorn backend.app.main:app"

_PROXY_PEER = ("10.0.0.2", 51234)
_PUBLIC_PEER = ("198.51.100.20", 51234)
_REAL_CLIENT = "203.0.113.50"
_LIMIT = 3


def _forged_first_hop(i: int) -> dict[str, str]:
    return {"X-Forwarded-For": f"198.18.0.{i}, {_REAL_CLIENT}"}


def _login_body(i: int) -> dict[str, str]:
    return {"email": f"stuffing{i}@test.com", "password": "wrong-pass-123"}


def _register_body(i: int) -> dict[str, str]:
    return {"email": f"xff-reg{i}@test.com", "password": "senha123", "full_name": f"U {i}"}


async def _client_from(peer: tuple[str, int]) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app, client=peer)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def via_proxy() -> AsyncIterator[AsyncClient]:
    async for ac in _client_from(_PROXY_PEER):
        yield ac


@pytest_asyncio.fixture
async def direct_public() -> AsyncIterator[AsyncClient]:
    async for ac in _client_from(_PUBLIC_PEER):
        yield ac


@pytest.fixture
def login_limit(monkeypatch) -> None:
    fake = fakeredis.FakeRedis()
    monkeypatch.setattr(rl, "_get_redis_safe", lambda: fake)
    monkeypatch.setattr(settings, "RATE_LIMIT_LOGIN", f"{_LIMIT}/60")


@pytest.fixture
def register_limit(monkeypatch) -> None:
    fake = fakeredis.FakeRedis()
    monkeypatch.setenv("MATHOMS_REGISTER_RATE_LIMIT_PER_HOUR", str(_LIMIT))
    monkeypatch.setattr(register_rl, "_resolve_client", lambda: fake)


def _assert_only_last_is_rate_limited(statuses: list[int]) -> None:
    assert 429 not in statuses[:_LIMIT], statuses
    assert statuses[_LIMIT] == 429, statuses


@pytest.mark.asyncio
async def test_login_primeiro_hop_forjado_rotativo_nao_escapa_do_limite(
    via_proxy: AsyncClient, login_limit: None
) -> None:
    statuses = [
        (
            await via_proxy.post(
                "/api/v1/auth/login", json=_login_body(i), headers=_forged_first_hop(i)
            )
        ).status_code
        for i in range(_LIMIT + 1)
    ]
    _assert_only_last_is_rate_limited(statuses)


@pytest.mark.asyncio
async def test_login_peer_nao_confiavel_nao_injeta_x_forwarded_for(
    direct_public: AsyncClient, login_limit: None
) -> None:
    statuses = [
        (
            await direct_public.post(
                "/api/v1/auth/login",
                json=_login_body(i),
                headers={"X-Forwarded-For": f"198.18.0.{i}"},
            )
        ).status_code
        for i in range(_LIMIT + 1)
    ]
    _assert_only_last_is_rate_limited(statuses)


@pytest.mark.asyncio
async def test_register_primeiro_hop_forjado_rotativo_nao_escapa_do_limite(
    via_proxy: AsyncClient, register_limit: None
) -> None:
    statuses = [
        (
            await via_proxy.post(
                "/api/v1/auth/register", json=_register_body(i), headers=_forged_first_hop(i)
            )
        ).status_code
        for i in range(_LIMIT + 1)
    ]
    _assert_only_last_is_rate_limited(statuses)


async def _resolve(peer: str, xff: str) -> Request:
    """Passa um scope pelo middleware com o mesmo trust que ``main.py`` instala."""
    resolved: dict[str, Scope] = {}

    async def _capture(scope, receive, send) -> None:  # noqa: ANN001
        resolved["scope"] = scope

    middleware = ProxyHeadersMiddleware(_capture, trusted_hosts=settings.FORWARDED_ALLOW_IPS)
    scope = {"type": "http", "client": (peer, 1), "headers": [(b"x-forwarded-for", xff.encode())]}
    await middleware(scope, None, None)  # type: ignore[arg-type]
    return Request(resolved["scope"])


@pytest.mark.asyncio
@pytest.mark.parametrize("peer", ["127.0.0.1", "10.0.1.7", "172.18.0.3", "192.168.65.2"])
async def test_peer_na_rede_privada_e_proxy_confiavel(peer: str) -> None:
    request = await _resolve(peer, f"198.18.0.1, {_REAL_CLIENT}")
    assert client_meta(request)[0] == _REAL_CLIENT


@pytest.mark.asyncio
@pytest.mark.parametrize("peer", ["198.51.100.20", "100.64.0.1", "::ffff:10.0.0.2"])
async def test_peer_fora_das_faixas_confiaveis_e_o_proprio_cliente(peer: str) -> None:
    request = await _resolve(peer, f"198.18.0.1, {_REAL_CLIENT}")
    assert client_meta(request)[0] == peer


@pytest.mark.parametrize("catch_all", ["*", "0.0.0.0/0", "::/0", "10.0.0.0/8, *"])
def test_trust_catch_all_aborta_o_boot(catch_all: str) -> None:
    with pytest.raises(ValidationError, match="catch-all"):
        Settings(FORWARDED_ALLOW_IPS=catch_all)


def test_trust_explicito_e_aceito() -> None:
    assert Settings(FORWARDED_ALLOW_IPS="10.0.1.0/24,::1").FORWARDED_ALLOW_IPS == "10.0.1.0/24,::1"


def _launch_commands(text: str) -> list[str]:
    """Comandos que sobem o app, com as continuações ``\\`` juntadas."""
    logical = re.sub(r"\\\n", " ", text).splitlines()
    return [line for line in logical if _APP_LAUNCH in line]


def test_launchers_deixam_o_trust_do_xff_para_o_app() -> None:
    """Com o CLI ligado, ``FORWARDED_ALLOW_IPS=*`` trocaria o cliente antes do app."""
    commands = {
        launcher: _launch_commands((_REPO_ROOT / launcher).read_text()) for launcher in _LAUNCHERS
    }
    assert all(commands.values()), commands
    for launcher, launches in commands.items():
        for command in launches:
            assert "--no-proxy-headers" in command, (launcher, command)
            assert "--forwarded-allow-ips" not in command, (launcher, command)
