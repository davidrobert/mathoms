"""Rate limit por janela fixa (W4-T04 · SR-018) — Redis INCR+EXPIRE, fail-open."""

from __future__ import annotations

import fakeredis
import pytest

import backend.app.services.rate_limit as rl
from backend.app.core.config import settings
from backend.app.services.rate_limit import (
    RateLimitPolicy,
    check_rate_limit,
    client_ip_key,
    resolve_policy,
    workspace_key,
)


@pytest.fixture()
def redis_client(monkeypatch):
    client = fakeredis.FakeRedis()
    monkeypatch.setattr(rl, "_get_redis_safe", lambda: client)
    return client


def test_permite_ate_o_limite_e_nega_depois(redis_client) -> None:
    policy = RateLimitPolicy("t", limit=3, window_s=60)
    results = [check_rate_limit(policy, "k")[0] for _ in range(4)]
    assert results == [True, True, True, False]


def test_denied_retorna_retry_after_do_ttl(redis_client) -> None:
    policy = RateLimitPolicy("t", limit=1, window_s=60)
    check_rate_limit(policy, "k")
    allowed, retry_after = check_rate_limit(policy, "k")
    assert allowed is False
    assert 0 < retry_after <= 60


def test_chaves_distintas_nao_compartilham_janela(redis_client) -> None:
    policy = RateLimitPolicy("t", limit=1, window_s=60)
    assert check_rate_limit(policy, "a")[0] is True
    assert check_rate_limit(policy, "b")[0] is True


def test_fail_open_sem_redis(monkeypatch) -> None:
    """Rate limit é proteção de abuso, não controle de acesso — outage não nega."""
    monkeypatch.setattr(rl, "_get_redis_safe", lambda: None)
    policy = RateLimitPolicy("t", limit=1, window_s=60)
    assert check_rate_limit(policy, "k") == (True, 0)


def test_fail_open_em_erro_de_redis(monkeypatch) -> None:
    class _Boom:
        def incr(self, *_):
            raise ConnectionError("redis down")

    monkeypatch.setattr(rl, "_get_redis_safe", lambda: _Boom())
    policy = RateLimitPolicy("t", limit=1, window_s=60)
    assert check_rate_limit(policy, "k") == (True, 0)


def test_resolve_policy_override_por_env(monkeypatch) -> None:
    monkeypatch.setattr(settings, "RATE_LIMIT_LOGIN", "99/120")
    policy = resolve_policy("login")
    assert (policy.limit, policy.window_s) == (99, 120)


def test_resolve_policy_override_invalido_cai_no_default(monkeypatch) -> None:
    monkeypatch.setattr(settings, "RATE_LIMIT_LOGIN", "banana")
    policy = resolve_policy("login")
    assert (policy.limit, policy.window_s) == (10, 60)


class _FakeRequest:
    def __init__(self, headers=None, host="10.0.0.9", path_params=None):
        self.headers = headers or {}
        self.path_params = path_params or {}
        self.client = type("C", (), {"host": host})() if host else None


def test_client_ip_key_respeita_x_forwarded_for() -> None:
    req = _FakeRequest(headers={"x-forwarded-for": "203.0.113.7, 10.0.0.1"})
    assert client_ip_key(req) == "203.0.113.7"


def test_workspace_key_usa_path_param_e_cai_no_ip() -> None:
    assert workspace_key(_FakeRequest(path_params={"workspace_id": "ws-1"})) == "ws-1"
    assert workspace_key(_FakeRequest(host="10.1.1.1")) == "10.1.1.1"


@pytest.mark.asyncio
async def test_login_endpoint_responde_429_apos_limite(client, monkeypatch) -> None:
    """Integração: dependency no endpoint real devolve 429 + Retry-After."""
    fake = fakeredis.FakeRedis()
    monkeypatch.setattr(rl, "_get_redis_safe", lambda: fake)
    monkeypatch.setattr(settings, "RATE_LIMIT_LOGIN", "2/60")

    payload = {"email": "rl@test.com", "password": "wrong-pass-123"}
    for _ in range(2):
        await client.post("/api/v1/auth/login", json=payload)
    resp = await client.post("/api/v1/auth/login", json=payload)

    assert resp.status_code == 429
    assert "Retry-After" in resp.headers
