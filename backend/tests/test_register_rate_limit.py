"""Tests para rate limit IP em /auth/register (post-review fix 0.6 parte 1)."""

from __future__ import annotations

from unittest.mock import patch

import pytest

import backend.app.services.security.register_rate_limit as rate_module


class _FakeRedis:
    """Backend in-memory minimal para simular incr/expire/ttl."""

    def __init__(self) -> None:
        self.values: dict[str, int] = {}
        self.ttls: dict[str, int] = {}

    def incr(self, key: str) -> int:
        self.values[key] = self.values.get(key, 0) + 1
        return self.values[key]

    def expire(self, key: str, ttl_s: int) -> None:
        self.ttls[key] = ttl_s

    def ttl(self, key: str) -> int:
        return self.ttls.get(key, 3600)


@pytest.fixture
def fake_redis(monkeypatch) -> _FakeRedis:
    """Fake Redis + reativa rate limit (conftest desabilita por default)."""
    monkeypatch.setenv(
        "MATHOMS_REGISTER_RATE_LIMIT_PER_HOUR",
        str(rate_module._DEFAULT_LIMIT_PER_HOUR),
    )
    fake = _FakeRedis()
    with patch.object(rate_module, "_resolve_client", return_value=fake):
        yield fake


def test_first_request_allowed(fake_redis: _FakeRedis) -> None:
    allowed, _ = rate_module.check_register_rate("1.2.3.4")
    assert allowed is True


def test_blocks_after_threshold(fake_redis: _FakeRedis) -> None:
    ip = "10.0.0.1"
    # default = 10. 11ª chamada deve bloquear.
    for _ in range(rate_module._DEFAULT_LIMIT_PER_HOUR):
        allowed, _ = rate_module.check_register_rate(ip)
        assert allowed is True
    allowed, retry_after = rate_module.check_register_rate(ip)
    assert allowed is False
    assert retry_after > 0


def test_no_ip_always_allowed(fake_redis: _FakeRedis) -> None:
    """Proxy mal configurado / IP ausente — falha aberta (não bloqueia)."""
    allowed, retry = rate_module.check_register_rate(None)
    assert allowed is True
    assert retry == 0


def test_redis_unavailable_falls_open() -> None:
    """Sem Redis → permite (mesmo trade-off do brute_force_lockout)."""
    with patch.object(rate_module, "_resolve_client", return_value=None):
        allowed, _ = rate_module.check_register_rate("9.9.9.9")
        assert allowed is True


def test_separate_ips_have_independent_buckets(fake_redis: _FakeRedis) -> None:
    for _ in range(rate_module._DEFAULT_LIMIT_PER_HOUR):
        rate_module.check_register_rate("10.1.1.1")
    # IP 10.1.1.1 esgotou; mas outro IP segue livre.
    allowed_other, _ = rate_module.check_register_rate("10.2.2.2")
    assert allowed_other is True


@pytest.mark.asyncio
async def test_register_endpoint_returns_429_after_limit(fake_redis: _FakeRedis, client) -> None:
    """/auth/register responde 429 com Retry-After após exceder o limite."""
    body = lambda i: {  # noqa: E731
        "email": f"flood{i}@test.com",
        "password": "senha123",
        "full_name": f"User {i}",
    }
    headers = {"X-Forwarded-For": "203.0.113.99"}
    for i in range(rate_module._DEFAULT_LIMIT_PER_HOUR):
        resp = await client.post("/api/auth/register", json=body(i), headers=headers)
        assert resp.status_code == 201, f"call {i} should succeed"
    # Próxima chamada do mesmo IP deve cair em 429.
    blocked = await client.post("/api/auth/register", json=body(99), headers=headers)
    assert blocked.status_code == 429
    assert "Retry-After" in blocked.headers
