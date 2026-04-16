"""Tests for Redis Pub/Sub event publisher."""

import json
from unittest.mock import MagicMock, patch

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


@pytest.fixture(autouse=True)
def reset_redis():
    reset_redis_client()
    yield
    reset_redis_client()


class TestPublishEvent:
    def test_publish_event_with_redis(self):
        mock_redis = MagicMock()
        with patch("backend.app.services.events._get_redis", return_value=mock_redis):
            publish_event("run-1", "stage_started", stage="E3", status="running", progress_pct=30)

        mock_redis.publish.assert_called_once()
        channel, payload_str = mock_redis.publish.call_args[0]
        assert channel == "pipeline:run-1"
        payload = json.loads(payload_str)
        assert payload["event"] == "stage_started"
        assert payload["run_id"] == "run-1"
        assert payload["stage"] == "E3"
        assert payload["status"] == "running"
        assert payload["progress_pct"] == 30
        assert "timestamp" in payload

    def test_publish_event_redis_unavailable(self):
        with patch("backend.app.services.events._get_redis", return_value=None):
            publish_event("run-1", "stage_started", stage="E3")

    def test_publish_event_redis_publish_error(self):
        mock_redis = MagicMock()
        mock_redis.publish.side_effect = ConnectionError("connection lost")
        with patch("backend.app.services.events._get_redis", return_value=mock_redis):
            publish_event("run-1", "stage_started", stage="E3")

    def test_publish_stage_started(self):
        mock_redis = MagicMock()
        with patch("backend.app.services.events._get_redis", return_value=mock_redis):
            publish_stage_started("run-1", "E3", 30)
        payload = json.loads(mock_redis.publish.call_args[0][1])
        assert payload["event"] == "stage_started"
        assert payload["stage"] == "E3"

    def test_publish_stage_completed(self):
        mock_redis = MagicMock()
        with patch("backend.app.services.events._get_redis", return_value=mock_redis):
            publish_stage_completed("run-1", "E3", 50)
        payload = json.loads(mock_redis.publish.call_args[0][1])
        assert payload["event"] == "stage_completed"

    def test_publish_stage_failed(self):
        mock_redis = MagicMock()
        with patch("backend.app.services.events._get_redis", return_value=mock_redis):
            publish_stage_failed("run-1", "E3", "boom", 50)
        payload = json.loads(mock_redis.publish.call_args[0][1])
        assert payload["event"] == "stage_failed"
        assert payload["error"] == "boom"

    def test_publish_stage_activity(self):
        mock_redis = MagicMock()
        with patch("backend.app.services.events._get_redis", return_value=mock_redis):
            publish_stage_activity(
                "run-1",
                "E2-llm",
                file="informe.pdf",
                message="Extraindo com IA…",
            )
        payload = json.loads(mock_redis.publish.call_args[0][1])
        assert payload["event"] == "stage_activity"
        assert payload["stage"] == "E2-llm"
        assert payload["detail"]["file"] == "informe.pdf"
        assert payload["detail"]["message"] == "Extraindo com IA…"

    def test_publish_stage_skipped(self):
        mock_redis = MagicMock()
        with patch("backend.app.services.events._get_redis", return_value=mock_redis):
            publish_stage_skipped("run-1", "E1", "free tier", 10)
        payload = json.loads(mock_redis.publish.call_args[0][1])
        assert payload["event"] == "stage_skipped"
        assert payload["detail"]["reason"] == "free tier"

    def test_publish_needs_review(self):
        mock_redis = MagicMock()
        with patch("backend.app.services.events._get_redis", return_value=mock_redis):
            publish_needs_review("run-1", "E7-review")
        payload = json.loads(mock_redis.publish.call_args[0][1])
        assert payload["event"] == "needs_review"

    def test_publish_run_completed(self):
        mock_redis = MagicMock()
        with patch("backend.app.services.events._get_redis", return_value=mock_redis):
            publish_run_completed("run-1")
        payload = json.loads(mock_redis.publish.call_args[0][1])
        assert payload["event"] == "run_completed"
        assert payload["progress_pct"] == 100

    def test_publish_run_failed(self):
        mock_redis = MagicMock()
        with patch("backend.app.services.events._get_redis", return_value=mock_redis):
            publish_run_failed("run-1")
        payload = json.loads(mock_redis.publish.call_args[0][1])
        assert payload["event"] == "run_failed"

    def test_publish_run_cancelled(self):
        mock_redis = MagicMock()
        with patch("backend.app.services.events._get_redis", return_value=mock_redis):
            publish_run_cancelled("run-1")
        payload = json.loads(mock_redis.publish.call_args[0][1])
        assert payload["event"] == "run_cancelled"

    def test_publish_event_with_detail(self):
        mock_redis = MagicMock()
        with patch("backend.app.services.events._get_redis", return_value=mock_redis):
            publish_event("run-1", "custom", detail={"key": "value"})
        payload = json.loads(mock_redis.publish.call_args[0][1])
        assert payload["detail"] == {"key": "value"}

    def test_publish_event_minimal_fields(self):
        mock_redis = MagicMock()
        with patch("backend.app.services.events._get_redis", return_value=mock_redis):
            publish_event("run-1", "test_event")
        payload = json.loads(mock_redis.publish.call_args[0][1])
        assert payload["event"] == "test_event"
        assert payload["run_id"] == "run-1"
        assert "stage" not in payload
        assert "error" not in payload
