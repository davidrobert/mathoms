"""Tests for `pipeline.live_progress` facade (ADR-119 LiveStep contract)."""

from __future__ import annotations

from unittest.mock import patch

from pipeline.live_progress import emit_item_progress, emit_stage_activity


class TestEmitStageActivity:
    def test_noop_without_run_id(self):
        with patch("backend.app.services.pipeline.events.publish_stage_activity") as mock:
            emit_stage_activity(None, "E1", message="x")
            emit_stage_activity("", "E1", message="x")
            assert mock.call_count == 0

    def test_forwards_fields_when_run_id_set(self):
        with patch("backend.app.services.pipeline.events.publish_stage_activity") as mock:
            emit_stage_activity("run-1", "E2-llm", file="a.pdf", message="ok", custom="x")
            mock.assert_called_once_with(
                "run-1", "E2-llm", file="a.pdf", message="ok", extra={"custom": "x"}
            )

    def test_swallows_backend_import_failure(self):
        with patch(
            "backend.app.services.pipeline.events.publish_stage_activity", side_effect=RuntimeError
        ):
            emit_stage_activity("run-1", "E1", message="x")


class TestEmitItemProgress:
    def test_noop_without_run_id(self):
        with patch("backend.app.services.pipeline.events.publish_item_progress") as mock:
            emit_item_progress(
                None, "E1.5", current_item="a", items_done=0, items_total=1, phase="preparing"
            )
            assert mock.call_count == 0

    def test_forwards_all_fields(self):
        with patch("backend.app.services.pipeline.events.publish_item_progress") as mock:
            emit_item_progress(
                "run-1",
                "E1.5",
                current_item="doc.pdf",
                items_done=2,
                items_total=5,
                phase="awaiting_llm",
                estimated_duration_ms=900_000,
            )
            mock.assert_called_once_with(
                "run-1",
                "E1.5",
                current_item="doc.pdf",
                items_done=2,
                items_total=5,
                phase="awaiting_llm",
                estimated_duration_ms=900_000,
            )

    def test_swallows_backend_failure(self):
        with patch(
            "backend.app.services.pipeline.events.publish_item_progress",
            side_effect=RuntimeError("boom"),
        ):
            emit_item_progress(
                "run-1", "E1.5", current_item="a", items_done=0, items_total=1, phase="preparing"
            )
