"""Tests — ``stage_duration_estimator`` cache (ADR-119 item 5)."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from backend.app.services.pipeline.events import reset_redis_client
from backend.app.services.pipeline.stage_duration_estimator import (
    _cache_key,
    get_cached_stage_estimates,
    invalidate_stage_estimates,
)
from backend.tests.fakes.fake_redis_publisher import FakeRedisPublisher


class _FakeRedisWithGet(FakeRedisPublisher):
    """Extende FakeRedisPublisher com get/delete para testar o cache."""

    def __init__(self) -> None:
        super().__init__()
        self._store: dict[str, str] = {}
        self.get_calls = 0
        self.set_calls = 0

    def get(self, key: str) -> str | None:
        self.get_calls += 1
        return self._store.get(key)

    def set(self, key, value, *, nx=False, px=None, ex=None):
        self.set_calls += 1
        if nx and key in self._store:
            return None
        self._store[key] = value
        return True

    def delete(self, key: str) -> int:
        return 1 if self._store.pop(key, None) is not None else 0


@pytest.fixture(autouse=True)
def reset_redis():
    reset_redis_client()
    yield
    reset_redis_client()


@pytest.fixture
def fake_redis():
    publisher = _FakeRedisWithGet()
    with patch("backend.app.services.pipeline.events._get_redis", return_value=publisher):
        yield publisher


def test_cache_hit_skips_db_query(fake_redis):
    fake_redis._store[_cache_key("ws-1")] = json.dumps({"E1.5": 15_000})
    sentinel = object()

    result = get_cached_stage_estimates(sentinel, "ws-1")  # type: ignore[arg-type]

    assert result == {"E1.5": 15_000}
    assert fake_redis.get_calls == 1
    # sentinel passaria se fosse usado — não é, porque cache hit.


def test_cache_miss_queries_and_populates(fake_redis):
    with patch(
        "backend.app.services.pipeline.stage_duration_estimator.PipelineStageLogRepository"
    ) as mock_repo_cls:
        mock_repo_cls.return_value.get_median_durations_for_workspace.return_value = {
            "E1.5": 20_000,
            "E3": 5_000,
        }
        result = get_cached_stage_estimates(object(), "ws-1")  # type: ignore[arg-type]

    assert result == {"E1.5": 20_000, "E3": 5_000}
    assert fake_redis._store[_cache_key("ws-1")] == json.dumps({"E1.5": 20_000, "E3": 5_000})


def test_db_failure_returns_empty_and_caches_empty(fake_redis):
    with patch(
        "backend.app.services.pipeline.stage_duration_estimator.PipelineStageLogRepository"
    ) as mock_repo_cls:
        mock_repo_cls.return_value.get_median_durations_for_workspace.side_effect = RuntimeError(
            "db boom"
        )
        result = get_cached_stage_estimates(object(), "ws-1")  # type: ignore[arg-type]

    assert result == {}
    # Empty ainda é cacheado — evita query repetida em DB down.
    assert fake_redis._store[_cache_key("ws-1")] == "{}"


def test_cache_parse_failure_falls_through_to_query(fake_redis):
    fake_redis._store[_cache_key("ws-1")] = "{garbled json"
    with patch(
        "backend.app.services.pipeline.stage_duration_estimator.PipelineStageLogRepository"
    ) as mock_repo_cls:
        mock_repo_cls.return_value.get_median_durations_for_workspace.return_value = {"E1.5": 9999}
        result = get_cached_stage_estimates(object(), "ws-1")  # type: ignore[arg-type]
    assert result == {"E1.5": 9999}


def test_invalidate_clears_cache(fake_redis):
    fake_redis._store[_cache_key("ws-1")] = json.dumps({"E1.5": 1000})
    invalidate_stage_estimates("ws-1")
    assert _cache_key("ws-1") not in fake_redis._store


def test_cache_key_is_per_workspace(fake_redis):
    fake_redis._store[_cache_key("ws-a")] = json.dumps({"E1.5": 1_000})
    fake_redis._store[_cache_key("ws-b")] = json.dumps({"E1.5": 2_000})

    assert get_cached_stage_estimates(object(), "ws-a") == {"E1.5": 1_000}  # type: ignore[arg-type]
    assert get_cached_stage_estimates(object(), "ws-b") == {"E1.5": 2_000}  # type: ignore[arg-type]
