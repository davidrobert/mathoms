"""A6f.3 — OpenTelemetry tracing tests using InMemorySpanExporter.

Validates:
- `setup_otel()` is idempotent (re-entry safe for Celery prefork/test harness).
- FastAPI instrumentation emits a span per HTTP request.
- Pipeline `_run_stage` wraps runners in `pipeline.{stage}` spans with
  declared attributes, even when the runner raises `SystemExit` (legacy
  script behavior) — the span must still be closed and carry
  `pipeline.success=False`.
- `opentelemetry.trace` is safe to import in `pipeline/` (no-op when no
  provider is configured).
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from starlette.testclient import TestClient

from pipeline.context import WorkspaceContext
from pipeline.orchestrator import _run_stage


@pytest.fixture
def in_memory_exporter(monkeypatch):
    """Install a fresh TracerProvider + InMemorySpanExporter for the test."""
    exporter = InMemorySpanExporter()
    provider = TracerProvider(
        resource=Resource.create({SERVICE_NAME: "mathoms-test"})
    )
    provider.add_span_processor(SimpleSpanProcessor(exporter))

    trace._TRACER_PROVIDER_SET_ONCE._done = False  # type: ignore[attr-defined]
    previous = trace.get_tracer_provider()
    trace.set_tracer_provider(provider)

    # orchestrator captured the tracer at import time; re-bind so new spans
    # land on our test provider.
    import pipeline.orchestrator as orch

    monkeypatch.setattr(orch, "_TRACER", trace.get_tracer("mathoms.pipeline.orchestrator"))

    yield exporter

    trace._TRACER_PROVIDER_SET_ONCE._done = False  # type: ignore[attr-defined]
    trace.set_tracer_provider(previous)


def test_setup_otel_is_idempotent(monkeypatch):
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    if "backend.app.core.otel" in sys.modules:
        del sys.modules["backend.app.core.otel"]
    otel = importlib.import_module("backend.app.core.otel")
    otel.setup_otel(service_name="mathoms-test")
    otel.setup_otel(service_name="mathoms-test")
    otel.setup_otel(service_name="mathoms-test")
    assert otel._INSTRUMENTED is True


def test_pipeline_stage_span_success_path(in_memory_exporter, tmp_path):
    """Runner succeeds → span closed with correct attributes."""
    ctx = WorkspaceContext(root=tmp_path, pipeline_run_id="run-abc")

    def fake_runner(ctx):  # noqa: ARG001
        return {"ok": True}

    import pipeline.orchestrator as orch

    original = orch._get_stage_runner
    orch._get_stage_runner = lambda stage: fake_runner
    try:
        result = _run_stage(ctx, "E3")
    finally:
        orch._get_stage_runner = original

    assert result.success is True

    spans = in_memory_exporter.get_finished_spans()
    names = [s.name for s in spans]
    assert "pipeline.E3" in names

    pipeline_span = next(s for s in spans if s.name == "pipeline.E3")
    assert pipeline_span.attributes["pipeline.stage"] == "E3"
    assert pipeline_span.attributes["pipeline.run_id"] == "run-abc"
    assert pipeline_span.attributes["pipeline.workspace_root"] == str(tmp_path.resolve())


def test_pipeline_stage_span_system_exit_closes_span(in_memory_exporter, tmp_path):
    """Legacy `sys.exit(1)` path still closes span with success=False."""
    ctx = WorkspaceContext(root=tmp_path)

    def failing_runner(ctx):  # noqa: ARG001
        raise SystemExit(1)

    import pipeline.orchestrator as orch

    original = orch._get_stage_runner
    orch._get_stage_runner = lambda stage: failing_runner
    try:
        result = _run_stage(ctx, "E5")
    finally:
        orch._get_stage_runner = original

    assert result.success is False

    spans = in_memory_exporter.get_finished_spans()
    pipeline_span = next(s for s in spans if s.name == "pipeline.E5")
    assert pipeline_span.attributes.get("pipeline.success") is False
    assert pipeline_span.attributes.get("pipeline.exit_code") == 1


def test_pipeline_stage_span_exception_records_exception(in_memory_exporter, tmp_path):
    """Generic exception path records exception and marks span failed."""
    ctx = WorkspaceContext(root=tmp_path)

    def raising_runner(ctx):  # noqa: ARG001
        raise RuntimeError("boom")

    import pipeline.orchestrator as orch

    original = orch._get_stage_runner
    orch._get_stage_runner = lambda stage: raising_runner
    try:
        result = _run_stage(ctx, "E4")
    finally:
        orch._get_stage_runner = original

    assert result.success is False
    assert "boom" in (result.error or "")

    spans = in_memory_exporter.get_finished_spans()
    pipeline_span = next(s for s in spans if s.name == "pipeline.E4")
    assert pipeline_span.attributes.get("pipeline.success") is False
    assert any(e.name == "exception" for e in pipeline_span.events)


def test_fastapi_instrumentation_emits_request_span(in_memory_exporter):
    """FastAPIInstrumentor wraps endpoints in HTTP server spans."""
    app = FastAPI()

    @app.get("/ping")
    def ping():
        return {"ok": True}

    FastAPIInstrumentor.instrument_app(app)
    try:
        client = TestClient(app)
        resp = client.get("/ping")
        assert resp.status_code == 200
    finally:
        FastAPIInstrumentor.uninstrument_app(app)

    spans = in_memory_exporter.get_finished_spans()
    # FastAPI instrumentation creates a span named "GET /ping" (Starlette default).
    assert any(s.name == "GET /ping" for s in spans), [s.name for s in spans]


def test_pipeline_boundary_safe_without_tracer(tmp_path, monkeypatch):
    """Pipeline orchestrator must not crash when `_TRACER` is None.

    Simulates the CLI-isolated case (OTel API not importable) — orchestrator
    falls back to ``nullcontext()`` and yields a ``None`` span, which guards
    in ``_run_stage`` must handle silently (ADR-110).
    """
    import pipeline.orchestrator as orch

    monkeypatch.setattr(orch, "_TRACER", None)

    ctx = WorkspaceContext(root=tmp_path)

    def fake_runner(ctx):  # noqa: ARG001
        return {"ok": True}

    original = orch._get_stage_runner
    orch._get_stage_runner = lambda stage: fake_runner
    try:
        result = _run_stage(ctx, "E3")
    finally:
        orch._get_stage_runner = original

    assert result.success is True

    # Exercise the SystemExit + Exception branches too — guards must no-op.
    def exiter(ctx):  # noqa: ARG001
        raise SystemExit(1)

    orch._get_stage_runner = lambda stage: exiter
    try:
        r2 = _run_stage(ctx, "E3")
    finally:
        orch._get_stage_runner = original
    assert r2.success is False

    def raiser(ctx):  # noqa: ARG001
        raise RuntimeError("x")

    orch._get_stage_runner = lambda stage: raiser
    try:
        r3 = _run_stage(ctx, "E3")
    finally:
        orch._get_stage_runner = original
    assert r3.success is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
