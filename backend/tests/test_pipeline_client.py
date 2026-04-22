"""Tests for PipelineServiceClient adapter (A6f.1 slice 2)."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

from backend.app.services.pipeline_client import (
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
