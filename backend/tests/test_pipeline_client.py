"""Tests for PipelineServiceClient adapter (A6f.1 slice 2 · ADR-323 fallback)."""

from __future__ import annotations

import logging
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

from backend.app.services.pipeline.pipeline_client import (
    FallbackPipelineClient,
    HttpPipelineClient,
    InProcessPipelineClient,
    StageResult,
    get_pipeline_client,
    reset_pipeline_client,
)


@pytest.fixture(autouse=True)
def _reset():
    reset_pipeline_client()
    yield
    reset_pipeline_client()


def _ctx(tmp_path: Path, run_id: str = "run-xyz") -> SimpleNamespace:
    """Minimal ctx duck — HttpPipelineClient only reads attributes it needs."""
    return SimpleNamespace(
        root=tmp_path,
        config_dir=tmp_path / "config",
        pipeline_run_id=run_id,
        incremental=False,
        incremental_doc_paths=[],
    )


def test_factory_defaults_to_inprocess(monkeypatch):
    monkeypatch.delenv("MATHOMS_PIPELINE_SERVICE_URL", raising=False)
    client = get_pipeline_client()
    assert isinstance(client, InProcessPipelineClient)


def test_factory_returns_http_when_env_set(monkeypatch):
    monkeypatch.setenv("MATHOMS_PIPELINE_SERVICE_URL", "http://mock")
    client = get_pipeline_client()
    assert isinstance(client, HttpPipelineClient)


def test_factory_is_singleton(monkeypatch):
    monkeypatch.delenv("MATHOMS_PIPELINE_SERVICE_URL", raising=False)
    assert get_pipeline_client() is get_pipeline_client()


def test_inprocess_is_llm_stage_reads_registry():
    client = InProcessPipelineClient()
    assert client.is_llm_stage("E1") is True
    assert client.is_llm_stage("E3") is False
    assert client.is_llm_stage("bogus") is False


def test_inprocess_execute_stage_delegates_to_orchestrator(tmp_path, monkeypatch):
    import pipeline.orchestrator as orch

    def fake(ctx, stage):
        return orch.StageResult(stage=stage, success=True, duration_ms=7.0, detail={"ok": 1})

    monkeypatch.setattr(orch, "_run_stage", fake)

    from pipeline.context import WorkspaceContext

    ctx = WorkspaceContext.for_tenant(tmp_path, pipeline_run_id="r")
    result = InProcessPipelineClient().execute_stage(ctx, "E3", workspace_id="ws")
    assert isinstance(result, StageResult)
    assert result.stage == "E3"
    assert result.success is True
    assert result.duration_ms == 7.0
    assert result.detail == {"ok": 1}


def test_http_execute_stage_translates_payload_and_response(tmp_path):
    captured: dict = {}

    def handler(req: httpx.Request) -> httpx.Response:
        captured["url"] = str(req.url)
        captured["body"] = req.content.decode()
        return httpx.Response(
            200,
            json={
                "stage": "E3",
                "success": True,
                "duration_ms": 12.3,
                "detail": {"touched": 2},
                "error": None,
                "attempts": 1,
            },
        )

    transport = httpx.MockTransport(handler)
    http = httpx.Client(transport=transport)
    client = HttpPipelineClient("http://ps.local", http=http)

    result = client.execute_stage(_ctx(tmp_path), "E3", workspace_id="ws-1")

    assert result.stage == "E3"
    assert result.success is True
    assert result.duration_ms == 12.3
    assert result.detail == {"touched": 2}
    assert "/api/v1/pipeline/stages/E3/execute" in captured["url"]
    import json as _json

    body = _json.loads(captured["body"])
    assert body["workspace_id"] == "ws-1"
    assert body["run_id"] == "run-xyz"
    assert body["incremental"] is False


def _skip_llm_no_payload(tmp_path, *, llm_calls_allowed: bool) -> bool:
    import json as _json

    captured: dict = {}

    def _record(req: httpx.Request) -> httpx.Response:
        captured.update(_json.loads(req.content.decode()))
        return httpx.Response(200, json={"stage": "E0", "success": True})

    transport = httpx.MockTransport(_record)
    client = HttpPipelineClient("http://ps.local", http=httpx.Client(transport=transport))
    ctx = _ctx(tmp_path)
    ctx.llm_calls_allowed = llm_calls_allowed
    client.execute_stage(ctx, "E0", workspace_id="ws-1")
    return captured["skip_llm"]


@pytest.mark.parametrize("llm_calls_allowed, esperado", [(False, True), (True, False)])
def test_http_payload_carries_run_llm_policy(tmp_path, llm_calls_allowed, esperado):
    """ADR-355: sem o campo o serviço rehidrata o ctx com LLM liberado."""
    assert _skip_llm_no_payload(tmp_path, llm_calls_allowed=llm_calls_allowed) is esperado


def test_http_execute_stage_translates_failure(tmp_path):
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "stage": "E4",
                "success": False,
                "duration_ms": 5.0,
                "detail": None,
                "error": "boom",
                "attempts": 1,
            },
        )

    http = httpx.Client(transport=httpx.MockTransport(handler))
    client = HttpPipelineClient("http://ps.local", http=http)

    result = client.execute_stage(_ctx(tmp_path), "E4", workspace_id="ws")
    assert result.success is False
    assert result.error == "boom"


def test_http_execute_stage_raises_on_5xx(tmp_path):
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"detail": "bad"})

    http = httpx.Client(transport=httpx.MockTransport(handler))
    client = HttpPipelineClient("http://ps.local", http=http)

    with pytest.raises(httpx.HTTPStatusError):
        client.execute_stage(_ctx(tmp_path), "E3", workspace_id="ws")


def test_http_client_splits_connect_and_read_timeout():
    """ADR-323: a dead shell must degrade fast (short connect), while long
    stages keep the generous read budget — not one flat 3600s for all."""
    client = HttpPipelineClient("http://ps.local")
    timeout = client._http.timeout
    assert timeout.connect == 5.0
    assert timeout.pool == 5.0
    assert timeout.read == 3600.0
    assert timeout.write == 3600.0


# --- ADR-323 auto-fallback (FallbackPipelineClient circuit breaker) --------


class _RecordingFallback:
    """InProcess stand-in — records calls, returns a canned InProcess result."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def execute_stage(self, ctx, stage: str, *, workspace_id: str) -> StageResult:
        self.calls.append((stage, workspace_id))
        return StageResult(stage=stage, success=True, duration_ms=1.0, detail={"ran": "inprocess"})

    def is_llm_stage(self, stage: str) -> bool:
        return False


class _ExplodingPrimary:
    """Primary that must never be reached once the circuit is open."""

    def execute_stage(self, ctx, stage: str, *, workspace_id: str) -> StageResult:
        raise AssertionError("primary must not be called when circuit is open")

    def is_llm_stage(self, stage: str) -> bool:
        return False


class _CountingConnectErrorPrimary:
    """Primary that always fails to connect, counting probes."""

    def __init__(self) -> None:
        self.calls = 0

    def execute_stage(self, ctx, stage: str, *, workspace_id: str) -> StageResult:
        self.calls += 1
        raise httpx.ConnectError("shell down")

    def is_llm_stage(self, stage: str) -> bool:
        return False


def _fallback_over(responder, fallback) -> FallbackPipelineClient:
    http = httpx.Client(transport=httpx.MockTransport(responder))
    return FallbackPipelineClient(HttpPipelineClient("http://ps.local", http=http), fallback)


def test_fallback_degrades_on_connect_error(tmp_path, caplog):
    def _raise_connect(req: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("shell down")

    fb = _RecordingFallback()
    client = _fallback_over(_raise_connect, fb)
    ctx = _ctx(tmp_path)

    with caplog.at_level(logging.ERROR, logger="mathoms.pipeline"):
        result = client.execute_stage(ctx, "E3", workspace_id="ws-1")

    assert result.success is True
    assert result.detail["ran"] == "inprocess"
    assert result.detail["_shell_fallback"] == {"executor": "inprocess", "trigger": "ConnectError"}
    assert fb.calls == [("E3", "ws-1")]
    assert ctx.shell_degraded is True
    events = [r for r in caplog.records if getattr(r, "event", None) == "pipeline_shell_fallback"]
    assert len(events) == 1
    assert events[0].trigger_class == "ConnectError"
    assert events[0].levelno == logging.ERROR


def test_fallback_degrades_on_5xx(tmp_path):
    # Looped (not parametrized) to keep one cheap fresh fake per status without
    # tripping the parametrize-recompute heuristic (ADR-210).
    for status in (500, 502, 503, 504):

        def _reply_5xx(req: httpx.Request, _s: int = status) -> httpx.Response:
            return httpx.Response(_s, json={"detail": "executor_unavailable"})

        fb = _RecordingFallback()
        client = _fallback_over(_reply_5xx, fb)
        ctx = _ctx(tmp_path)
        result = client.execute_stage(ctx, "E3", workspace_id="ws")
        assert result.success is True
        assert result.detail["_shell_fallback"]["trigger"] == f"http_{status}"
        assert fb.calls == [("E3", "ws")]
        assert ctx.shell_degraded is True


def test_no_fallback_on_domain_failure(tmp_path):
    """200 + success=False is a real stage failure — propagate, never degrade (would mask it)."""

    def _reply_domain_fail(req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"stage": "E4", "success": False, "error": "boom"})

    fb = _RecordingFallback()
    client = _fallback_over(_reply_domain_fail, fb)
    ctx = _ctx(tmp_path)
    result = client.execute_stage(ctx, "E4", workspace_id="ws")
    assert result.success is False
    assert result.error == "boom"
    assert "_shell_fallback" not in (result.detail or {})
    assert fb.calls == []
    assert getattr(ctx, "shell_degraded", False) is False


def test_no_fallback_on_4xx(tmp_path):
    """4xx is a contract bug (unknown stage / bad payload) — hard-fail, don't degrade."""

    def _reply_404(req: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"detail": "unknown stage"})

    fb = _RecordingFallback()
    client = _fallback_over(_reply_404, fb)
    ctx = _ctx(tmp_path)
    with pytest.raises(httpx.HTTPStatusError):
        client.execute_stage(ctx, "bogus", workspace_id="ws")
    assert fb.calls == []
    assert getattr(ctx, "shell_degraded", False) is False


def test_no_fallback_on_read_timeout(tmp_path):
    """ReadTimeout: the stage may still be running on the shell and commit later —
    re-running InProcess risks a concurrent double-write."""

    def _raise_read_timeout(req: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow stage")

    fb = _RecordingFallback()
    client = _fallback_over(_raise_read_timeout, fb)
    ctx = _ctx(tmp_path)
    with pytest.raises(httpx.ReadTimeout):
        client.execute_stage(ctx, "E5", workspace_id="ws")
    assert fb.calls == []
    assert getattr(ctx, "shell_degraded", False) is False


def test_circuit_open_skips_primary(tmp_path):
    fb = _RecordingFallback()
    client = FallbackPipelineClient(_ExplodingPrimary(), fb)
    ctx = _ctx(tmp_path)
    ctx.shell_degraded = True

    result = client.execute_stage(ctx, "E4", workspace_id="ws")

    assert result.detail["_shell_fallback"]["trigger"] is None
    assert fb.calls == [("E4", "ws")]


def test_sticky_degrade_probes_shell_once_per_run(tmp_path, caplog):
    """Circuit breaker: one probe, one telemetry event — later stages go straight
    to InProcess instead of re-probing a downed shell on every stage."""
    primary = _CountingConnectErrorPrimary()
    fb = _RecordingFallback()
    client = FallbackPipelineClient(primary, fb)
    ctx = _ctx(tmp_path)

    with caplog.at_level(logging.ERROR, logger="mathoms.pipeline"):
        client.execute_stage(ctx, "E3", workspace_id="ws")
        client.execute_stage(ctx, "E4", workspace_id="ws")

    assert primary.calls == 1  # only the first stage probed the shell
    assert [c[0] for c in fb.calls] == ["E3", "E4"]
    assert ctx.shell_degraded is True
    events = [r for r in caplog.records if getattr(r, "event", None) == "pipeline_shell_fallback"]
    assert len(events) == 1  # loud once, not once-per-stage


def test_degrade_state_is_per_run_not_shared(tmp_path):
    """Sticky state lives on ctx, never on the (singleton) client — two runs
    sharing one FallbackPipelineClient must not cross-poison (ADR-111)."""
    primary = _CountingConnectErrorPrimary()
    client = FallbackPipelineClient(primary, _RecordingFallback())
    ctx_a = _ctx(tmp_path, run_id="run-a")
    ctx_b = _ctx(tmp_path, run_id="run-b")

    client.execute_stage(ctx_a, "E3", workspace_id="ws")
    assert ctx_a.shell_degraded is True
    assert getattr(ctx_b, "shell_degraded", False) is False

    client.execute_stage(ctx_b, "E3", workspace_id="ws")
    assert primary.calls == 2  # run B's circuit was closed — it probed independently


def test_factory_wraps_in_fallback_when_enabled(monkeypatch):
    monkeypatch.setenv("MATHOMS_PIPELINE_SERVICE_URL", "http://mock")
    monkeypatch.setenv("MATHOMS_PIPELINE_SHELL_FALLBACK", "1")
    client = get_pipeline_client()
    assert isinstance(client, FallbackPipelineClient)


def test_factory_raw_http_when_fallback_disabled(monkeypatch):
    monkeypatch.setenv("MATHOMS_PIPELINE_SERVICE_URL", "http://mock")
    monkeypatch.delenv("MATHOMS_PIPELINE_SHELL_FALLBACK", raising=False)
    client = get_pipeline_client()
    assert isinstance(client, HttpPipelineClient)
    assert not isinstance(client, FallbackPipelineClient)


def test_factory_inprocess_ignores_fallback_flag(monkeypatch):
    monkeypatch.delenv("MATHOMS_PIPELINE_SERVICE_URL", raising=False)
    monkeypatch.setenv("MATHOMS_PIPELINE_SHELL_FALLBACK", "1")
    client = get_pipeline_client()
    assert isinstance(client, InProcessPipelineClient)
