"""Tests for Redis Pub/Sub event publisher."""

from unittest.mock import patch

import pytest

from backend.app.services.events import (
    publish_event,
    publish_run_cancelled,
    publish_run_completed,
    publish_run_failed,
    publish_stage_activity,
    publish_stage_completed,
    publish_stage_failed,
    publish_stage_skipped,
    publish_stage_started,
    publish_needs_review,
    reset_redis_client,
)
from backend.tests.fakes.fake_redis_publisher import FakeRedisPublisher


@pytest.fixture(autouse=True)
def reset_redis():
    reset_redis_client()
    yield
    reset_redis_client()


@pytest.fixture
def fake_redis():
    publisher = FakeRedisPublisher()
    with patch("backend.app.services.events._get_redis", return_value=publisher):
        yield publisher


class TestPublishEvent:
    def test_publish_event_includes_all_provided_fields(self, fake_redis):
        publish_event("run-1", "stage_started", stage="E3", status="running", progress_pct=30)

        msg = fake_redis.assert_published_once()
        assert msg.channel == "pipeline:run-1"
        payload = msg.payload
        assert payload["event"] == "stage_started"
        assert payload["run_id"] == "run-1"
        assert payload["stage"] == "E3"
        assert payload["status"] == "running"
        assert payload["progress_pct"] == 30
        assert "timestamp" in payload

    def test_publish_event_noops_when_redis_unavailable(self):
        with patch("backend.app.services.events._get_redis", return_value=None):
            publish_event("run-1", "stage_started", stage="E3")

    def test_publish_event_swallows_redis_connection_error(self):
        publisher = FakeRedisPublisher(publish_error=ConnectionError("connection lost"))
        with patch("backend.app.services.events._get_redis", return_value=publisher):
            publish_event("run-1", "stage_started", stage="E3")

    def test_publish_stage_started(self, fake_redis):
        publish_stage_started("run-1", "E3", 30)
        payload = fake_redis.last.payload
        assert payload["event"] == "stage_started"
        assert payload["stage"] == "E3"

    def test_publish_stage_completed(self, fake_redis):
        publish_stage_completed("run-1", "E3", 50)
        assert fake_redis.last.payload["event"] == "stage_completed"

    def test_publish_stage_failed(self, fake_redis):
        publish_stage_failed("run-1", "E3", "boom", 50)
        payload = fake_redis.last.payload
        assert payload["event"] == "stage_failed"
        assert payload["error"] == "boom"

    def test_publish_stage_activity(self, fake_redis):
        publish_stage_activity(
            "run-1",
            "E2-llm",
            file="informe.pdf",
            message="Extraindo com IA…",
        )
        payload = fake_redis.last.payload
        assert payload["event"] == "stage_activity"
        assert payload["stage"] == "E2-llm"
        assert payload["detail"]["file"] == "informe.pdf"
        assert payload["detail"]["message"] == "Extraindo com IA…"

    def test_publish_stage_skipped(self, fake_redis):
        publish_stage_skipped("run-1", "E1", "free tier", 10)
        payload = fake_redis.last.payload
        assert payload["event"] == "stage_skipped"
        assert payload["detail"]["reason"] == "free tier"

    def test_publish_needs_review(self, fake_redis):
        publish_needs_review("run-1", "E7-review")
        assert fake_redis.last.payload["event"] == "needs_review"

    def test_publish_run_completed(self, fake_redis):
        publish_run_completed("run-1")
        payload = fake_redis.last.payload
        assert payload["event"] == "run_completed"
        assert payload["progress_pct"] == 100

    def test_publish_run_failed(self, fake_redis):
        publish_run_failed("run-1")
        assert fake_redis.last.payload["event"] == "run_failed"

    def test_publish_run_cancelled(self, fake_redis):
        publish_run_cancelled("run-1")
        assert fake_redis.last.payload["event"] == "run_cancelled"

    def test_publish_event_with_detail(self, fake_redis):
        publish_event("run-1", "custom", detail={"key": "value"})
        assert fake_redis.last.payload["detail"] == {"key": "value"}

    def test_publish_event_minimal_fields(self, fake_redis):
        publish_event("run-1", "test_event")
        payload = fake_redis.last.payload
        assert payload["event"] == "test_event"
        assert payload["run_id"] == "run-1"
        assert "stage" not in payload
        assert "error" not in payload
