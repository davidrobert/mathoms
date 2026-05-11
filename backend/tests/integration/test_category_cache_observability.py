"""Integration: log estruturado ``mathoms.cache.requests`` emitido em hit/miss/fallback (SRE follow-up #192)."""

from __future__ import annotations

import logging

import pytest

from backend.app.services import category_cache


class _FakeRedis:
    def __init__(self, store: dict[str, str] | None = None) -> None:
        self._store: dict[str, str] = store or {}

    def get(self, key: str) -> str | None:
        return self._store.get(key)

    def set(self, key: str, value: str, ex: int | None = None) -> None:
        self._store[key] = value

    def delete(self, *keys: str) -> int:
        n = 0
        for k in keys:
            if k in self._store:
                del self._store[k]
                n += 1
        return n

    def scan_iter(self, match: str):
        if not match.endswith("*"):
            yield from (k for k in list(self._store) if k == match)
            return
        prefix = match[:-1]
        yield from (k for k in list(self._store) if k.startswith(prefix))


def _cache_events(records: list[logging.LogRecord]) -> list[dict]:
    """Extrai apenas eventos ``mathoms.cache.requests`` com campos ``cache``/``result``."""
    return [
        {"cache": r.cache, "result": r.result}
        for r in records
        if r.name == "mathoms.cache.requests"
    ]


def test_latest_template_version_miss_emits_event(
    monkeypatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(category_cache, "_get_redis_safe", lambda: _FakeRedis())
    with caplog.at_level(logging.INFO, logger="mathoms.cache.requests"):
        assert category_cache.get_latest_template_version() is None
    events = _cache_events(caplog.records)
    assert events == [{"cache": "latest_template_version", "result": "miss"}]


def test_latest_template_version_hit_emits_event(
    monkeypatch, caplog: pytest.LogCaptureFixture
) -> None:
    fake = _FakeRedis({"categories:latest_template_version": "7"})
    monkeypatch.setattr(category_cache, "_get_redis_safe", lambda: fake)
    with caplog.at_level(logging.INFO, logger="mathoms.cache.requests"):
        assert category_cache.get_latest_template_version() == 7
    events = _cache_events(caplog.records)
    assert events == [{"cache": "latest_template_version", "result": "hit"}]


def test_redis_offline_emits_fallback_event(monkeypatch, caplog: pytest.LogCaptureFixture) -> None:
    monkeypatch.setattr(category_cache, "_get_redis_safe", lambda: None)
    with caplog.at_level(logging.INFO, logger="mathoms.cache.requests"):
        assert category_cache.get_latest_template_version() is None
    events = _cache_events(caplog.records)
    assert events == [{"cache": "latest_template_version", "result": "fallback"}]


def test_redis_exception_emits_fallback_event(
    monkeypatch, caplog: pytest.LogCaptureFixture
) -> None:
    class _Broken:
        def get(self, key: str) -> str | None:
            raise RuntimeError("redis down mid-flight")

    monkeypatch.setattr(category_cache, "_get_redis_safe", lambda: _Broken())
    with caplog.at_level(logging.INFO, logger="mathoms.cache.requests"):
        assert category_cache.get_latest_template_version() is None
    events = _cache_events(caplog.records)
    assert events == [{"cache": "latest_template_version", "result": "fallback"}]


def test_resolved_categories_miss_emits_event(
    monkeypatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(category_cache, "_get_redis_safe", lambda: _FakeRedis())
    with caplog.at_level(logging.INFO, logger="mathoms.cache.requests"):
        assert category_cache.get_cached_resolved("ws-1", 1) is None
    events = _cache_events(caplog.records)
    assert events == [{"cache": "resolved_categories", "result": "miss"}]


def test_resolved_categories_hit_emits_event(monkeypatch, caplog: pytest.LogCaptureFixture) -> None:
    fake = _FakeRedis({"categories:ws=ws-1:v=1": "[]"})
    monkeypatch.setattr(category_cache, "_get_redis_safe", lambda: fake)
    with caplog.at_level(logging.INFO, logger="mathoms.cache.requests"):
        assert category_cache.get_cached_resolved("ws-1", 1) == []
    events = _cache_events(caplog.records)
    assert events == [{"cache": "resolved_categories", "result": "hit"}]


def test_category_template_miss_emits_event(monkeypatch, caplog: pytest.LogCaptureFixture) -> None:
    monkeypatch.setattr(category_cache, "_get_redis_safe", lambda: _FakeRedis())
    with caplog.at_level(logging.INFO, logger="mathoms.cache.requests"):
        assert category_cache.get_cached_template(1) is None
    events = _cache_events(caplog.records)
    assert events == [{"cache": "category_template", "result": "miss"}]


def test_ttl_constant_is_15_minutes() -> None:
    """TTL reduzido de 1h para 15min (SRE follow-up #192) — blast radius menor."""
    assert category_cache._LATEST_TEMPLATE_VERSION_TTL_SECONDS == 900
