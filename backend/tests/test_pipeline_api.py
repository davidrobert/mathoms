"""Tests for Pipeline API — trigger, status, list, cancel."""

from unittest.mock import patch, MagicMock

import pytest
from httpx import AsyncClient

_START = "backend.app.api.pipeline.start_pipeline_run"
_CANCEL = "backend.app.api.pipeline.cancel_pipeline_run"


# ---------------------------------------------------------------------------
# Trigger
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_trigger_pipeline_default(auth_client: AsyncClient):
    with patch(_START) as mock_start:
        resp = await auth_client.post("/api/pipeline/run", json={})
    assert resp.status_code == 202
    data = resp.json()
    assert data["status"] == "pending"
    assert data["id"]
    assert data["workspace_id"]
    assert data["total_documents"] is not None
    mock_start.assert_called_once()
    call_kwargs = mock_start.call_args
    assert call_kwargs.kwargs["skip_llm"] is True
    assert call_kwargs.kwargs["stop_on_error"] is True


@pytest.mark.asyncio
async def test_trigger_pipeline_from_stage(auth_client: AsyncClient):
    with patch(_START) as mock_start:
        resp = await auth_client.post(
            "/api/pipeline/run", json={"from_stage": "E3", "skip_llm": True}
        )
    assert resp.status_code == 202
    args = mock_start.call_args
    stages = args[1]["stages"] if "stages" in args[1] else args.kwargs.get("stages") or args[0][2]
    assert "E3" in stages


@pytest.mark.asyncio
async def test_trigger_pipeline_invalid_from_stage(auth_client: AsyncClient):
    with patch(_START):
        resp = await auth_client.post(
            "/api/pipeline/run", json={"from_stage": "E99"}
        )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_trigger_pipeline_concurrent_blocked(auth_client: AsyncClient):
    with patch(_START):
        resp1 = await auth_client.post("/api/pipeline/run", json={})
    assert resp1.status_code == 202

    with patch(_START):
        resp2 = await auth_client.post("/api/pipeline/run", json={})
    assert resp2.status_code == 409
    assert "ativa" in resp2.json()["detail"].lower()


# ---------------------------------------------------------------------------
# List runs
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_runs_empty(auth_client: AsyncClient):
    resp = await auth_client.get("/api/pipeline/runs")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["runs"] == []


@pytest.mark.asyncio
async def test_list_runs_after_trigger(auth_client: AsyncClient):
    with patch(_START):
        await auth_client.post("/api/pipeline/run", json={})
    resp = await auth_client.get("/api/pipeline/runs")
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1


# ---------------------------------------------------------------------------
# Get run detail
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_run_detail(auth_client: AsyncClient):
    with patch(_START):
        trigger_resp = await auth_client.post("/api/pipeline/run", json={})
    run_id = trigger_resp.json()["id"]

    resp = await auth_client.get(f"/api/pipeline/runs/{run_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == run_id
    assert "stage_logs" in data


@pytest.mark.asyncio
async def test_get_run_not_found(auth_client: AsyncClient):
    resp = await auth_client.get("/api/pipeline/runs/nonexistent")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Cancel
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cancel_active_run(auth_client: AsyncClient):
    with patch(_START):
        trigger_resp = await auth_client.post("/api/pipeline/run", json={})
    run_id = trigger_resp.json()["id"]

    with patch(_CANCEL, return_value=True):
        resp = await auth_client.post(f"/api/pipeline/runs/{run_id}/cancel")
    assert resp.status_code == 200
    assert "cancelamento" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_cancel_not_found(auth_client: AsyncClient):
    with patch(_CANCEL, return_value=False):
        resp = await auth_client.post("/api/pipeline/runs/nonexistent/cancel")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_cancel_already_completed(auth_client: AsyncClient):
    with patch(_START):
        trigger_resp = await auth_client.post("/api/pipeline/run", json={})
    run_id = trigger_resp.json()["id"]

    from backend.app.models.pipeline_run import PipelineRunStatus
    from backend.app.core.database import get_db
    from backend.app.main import app

    async for db in app.dependency_overrides[get_db]():
        from sqlalchemy import update
        from backend.app.models.pipeline_run import PipelineRun
        await db.execute(
            update(PipelineRun)
            .where(PipelineRun.id == run_id)
            .values(status=PipelineRunStatus.completed)
        )
        await db.commit()

    with patch(_CANCEL, return_value=False):
        resp = await auth_client.post(f"/api/pipeline/runs/{run_id}/cancel")
    assert resp.status_code == 409


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_pipeline_unauthorized(client: AsyncClient):
    resp = await client.post("/api/pipeline/run", json={})
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_list_runs_unauthorized(client: AsyncClient):
    resp = await client.get("/api/pipeline/runs")
    assert resp.status_code in (401, 403)
