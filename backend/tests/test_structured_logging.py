"""A6f.3 — structured JSON logging + correlation middleware tests.

Validates:
- `setup_logging()` emits parseable JSON with required fields.
- `MathomsJsonFormatter` picks up trace/workspace/user/run IDs from contextvars.
- `CorrelationIdMiddleware` propagates `X-Trace-Id` end-to-end and reflects
  it back on the response.
- `setup_otel()` runs without an OTLP endpoint (opt-in behavior).
"""

from __future__ import annotations

import importlib
import io
import json
import logging
import os
import sys
from contextlib import contextmanager

import pytest
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from backend.app.core.logging import (
    MathomsJsonFormatter,
    get_logger,
    setup_logging,
)
from backend.app.middleware.correlation import (
    TRACE_ID_HEADER,
    CorrelationIdMiddleware,
    set_pipeline_run_id,
    set_trace_id,
    set_user_id,
    set_workspace_id,
)


@contextmanager
def _captured_root_handler():
    """Replace root handlers with one writing JSON to a StringIO buffer."""
    root = logging.getLogger()
    saved_handlers = list(root.handlers)
    saved_level = root.level
    buf = io.StringIO()
    handler = logging.StreamHandler(buf)
    handler.setFormatter(MathomsJsonFormatter())
    root.handlers = [handler]
    root.setLevel(logging.DEBUG)
    try:
        yield buf
    finally:
        root.handlers = saved_handlers
        root.setLevel(saved_level)


def _lines(buf: io.StringIO) -> list[dict]:
    return [json.loads(line) for line in buf.getvalue().splitlines() if line.strip()]


def test_formatter_emits_parseable_json_with_required_fields():
    with _captured_root_handler() as buf:
        log = get_logger("unit.test.logger")
        log.info("hello world")

    records = _lines(buf)
    assert len(records) == 1
    r = records[0]
    assert r["message"] == "hello world"
    assert r["level"] == "INFO"
    assert r["logger"] == "mathoms.unit.test.logger"
    assert r["timestamp"].endswith("Z")
    assert "T" in r["timestamp"]


def test_formatter_includes_correlation_context():
    trace_tok = set_trace_id("trace-A")
    ws_tok = set_workspace_id("ws-42")
    user_tok = set_user_id("user-7")
    run_tok = set_pipeline_run_id("run-9")
    try:
        with _captured_root_handler() as buf:
            get_logger("ctx.test").warning("with ctx")
    finally:
        # contextvars auto-clean when tokens fall out of scope; but be
        # explicit so later tests do not leak state.
        import backend.app.middleware.correlation as mc  # noqa: WPS433

        mc._trace_id.reset(trace_tok)
        mc._workspace_id.reset(ws_tok)
        mc._user_id.reset(user_tok)
        mc._pipeline_run_id.reset(run_tok)

    r = _lines(buf)[0]
    assert r["trace_id"] == "trace-A"
    assert r["workspace_id"] == "ws-42"
    assert r["user_id"] == "user-7"
    assert r["pipeline_run_id"] == "run-9"


def test_formatter_omits_missing_context_fields():
    with _captured_root_handler() as buf:
        get_logger("clean.ctx").info("no ctx")
    r = _lines(buf)[0]
    assert "trace_id" not in r
    assert "workspace_id" not in r
    assert "user_id" not in r
    assert "pipeline_run_id" not in r


def test_setup_logging_is_idempotent():
    setup_logging()
    setup_logging()
    setup_logging()
    root = logging.getLogger()
    managed = [h for h in root.handlers if getattr(h, "_mathoms_managed", False)]
    assert len(managed) == 1


def test_correlation_middleware_generates_and_reflects_trace_id():
    async def handler(request):
        from backend.app.middleware.correlation import get_trace_id

        tid = get_trace_id()
        return PlainTextResponse(tid or "")

    app = Starlette(routes=[Route("/echo", handler)])
    app.add_middleware(CorrelationIdMiddleware)

    client = TestClient(app)
    resp = client.get("/echo")
    assert resp.status_code == 200
    reflected = resp.headers[TRACE_ID_HEADER]
    assert reflected
    assert resp.text == reflected


def test_correlation_middleware_honors_incoming_header():
    async def handler(request):
        from backend.app.middleware.correlation import get_trace_id

        return PlainTextResponse(get_trace_id() or "")

    app = Starlette(routes=[Route("/echo", handler)])
    app.add_middleware(CorrelationIdMiddleware)

    client = TestClient(app)
    resp = client.get("/echo", headers={TRACE_ID_HEADER: "deadbeef-1234"})
    assert resp.headers[TRACE_ID_HEADER] == "deadbeef-1234"
    assert resp.text == "deadbeef-1234"


def test_setup_otel_without_endpoint_does_not_raise(monkeypatch):
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    # Force a fresh import so _INSTRUMENTED is reset.
    if "backend.app.core.otel" in sys.modules:
        del sys.modules["backend.app.core.otel"]
    otel = importlib.import_module("backend.app.core.otel")
    otel.setup_otel(service_name="mathoms-test")
    assert otel.is_otel_enabled() is False


def test_json_lines_are_jq_compatible():
    """Each emitted line must be standalone JSON — no multi-line records."""
    with _captured_root_handler() as buf:
        log = get_logger("jq.test")
        log.info("line 1")
        log.warning("line 2")
        log.error("line 3", extra={"custom": {"nested": "ok"}})

    for line in buf.getvalue().splitlines():
        if line.strip():
            json.loads(line)  # would raise if not valid JSON


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
