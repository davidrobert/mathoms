"""Tests for Redis Pub/Sub event publisher."""

from unittest.mock import patch

import pytest

from backend.app.services.events import (
    publish_event,
    publish_item_progress,
    publish_needs_review,
    publish_run_cancelled,
    publish_run_completed,
    publish_run_failed,
    publish_stage_activity,
    publish_stage_completed,
    publish_stage_failed,
    publish_stage_skipped,
    publish_stage_started,
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


class TestPublishItemProgress:
    """ADR-119 — contrato LiveStep."""

    def test_emits_all_contract_fields(self, fake_redis):
        publish_item_progress(
            "run-1",
            "E1.5",
            current_item="declaracao_david.pdf",
            items_done=2,
            items_total=5,
            phase="awaiting_llm",
            estimated_duration_ms=900_000,
        )
        payload = fake_redis.last.payload
        assert payload["event"] == "stage_activity"
        assert payload["stage"] == "E1.5"
        assert payload["status"] == "running"
        detail = payload["detail"]
        assert detail["current_item"] == "declaracao_david.pdf"
        assert detail["items_done"] == 2
        assert detail["items_total"] == 5
        assert detail["phase"] == "awaiting_llm"
        assert detail["estimated_duration_ms"] == 900_000

    def test_omits_optional_fields_when_none(self, fake_redis):
        publish_item_progress(
            "run-1", "E2-llm", current_item=None, items_done=0, items_total=3, phase="preparing"
        )
        detail = fake_redis.last.payload["detail"]
        assert "current_item" not in detail
        assert "estimated_duration_ms" not in detail
        assert detail["items_done"] == 0

    def test_throttles_rapid_consecutive_emits(self, fake_redis):
        publish_item_progress(
            "run-1", "E1.5", current_item="a.pdf", items_done=0, items_total=5, phase="preparing"
        )
        publish_item_progress(
            "run-1",
            "E1.5",
            current_item="a.pdf",
            items_done=0,
            items_total=5,
            phase="awaiting_llm",
        )
        assert len(fake_redis.messages) == 1

    def test_finalizing_phase_bypasses_throttle(self, fake_redis):
        publish_item_progress(
            "run-1", "E1.5", current_item="a.pdf", items_done=4, items_total=5, phase="preparing"
        )
        publish_item_progress(
            "run-1", "E1.5", current_item="e.pdf", items_done=5, items_total=5, phase="finalizing"
        )
        assert len(fake_redis.messages) == 2
        assert fake_redis.last.payload["detail"]["phase"] == "finalizing"

    def test_throttle_is_per_stage(self, fake_redis):
        publish_item_progress(
            "run-1", "E1", current_item=None, items_done=0, items_total=2, phase="preparing"
        )
        publish_item_progress(
            "run-1", "E1.5", current_item=None, items_done=0, items_total=5, phase="preparing"
        )
        assert len(fake_redis.messages) == 2

    def test_throttle_is_per_run(self, fake_redis):
        publish_item_progress(
            "run-a", "E1.5", current_item=None, items_done=0, items_total=5, phase="preparing"
        )
        publish_item_progress(
            "run-b", "E1.5", current_item=None, items_done=0, items_total=5, phase="preparing"
        )
        assert len(fake_redis.messages) == 2

    def test_rejects_invalid_phase(self, fake_redis):
        with pytest.raises(ValueError, match="invalid LiveStep phase"):
            publish_item_progress(
                "run-1",
                "E1.5",
                current_item=None,
                items_done=0,
                items_total=1,
                phase="wat",  # type: ignore[arg-type]
            )

    def test_rejects_items_done_out_of_range(self, fake_redis):
        with pytest.raises(ValueError, match="out of"):
            publish_item_progress(
                "run-1", "E1.5", current_item=None, items_done=6, items_total=5, phase="preparing"
            )
        with pytest.raises(ValueError, match="out of"):
            publish_item_progress(
                "run-1", "E1.5", current_item=None, items_done=-1, items_total=5, phase="preparing"
            )
