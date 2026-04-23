"""Tests for Pipeline API — trigger, status, list, cancel."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.models.document import Document, DocumentStatus, DocumentType
from backend.tests.helpers.if_goal_stub import build_if_goal_stub

_START = "backend.app.application.pipeline_run.trigger_pipeline.start_pipeline_run"
_CANCEL = "backend.app.application.pipeline_run.cancel_run.cancel_pipeline_run"


# ---------------------------------------------------------------------------
# Trigger
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_trigger_incremental_rejects_when_no_stored_paths(
    auth_client: AsyncClient, db: AsyncSession
):
    """Incremental mode requires new docs to have a non-null stored_path."""
    ws_id = auth_client.ws_id
    data_dir = Path(settings.STORAGE_ROOT) / ws_id / "data" / "financial_statements"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "placeholder-0_original.pdf").write_bytes(b"x")

    db.add(
        Document(
            workspace_id=ws_id,
            original_name="orphan.pdf",
            stored_path=None,
            doc_type=DocumentType.bank_statement,
            bank_code="itau",
            period="202601",
            status=DocumentStatus.ready,
            file_size_bytes=1,
            content_hash="no-path-test-hash-000000000000",
        )
    )
    db.add(build_if_goal_stub(ws_id))
    await db.commit()

    with patch(_START):
        resp = await auth_client.post(
            f"/api/workspaces/{ws_id}/pipeline/run",
            json={"incremental": True, "skip_llm": True},
        )
    assert resp.status_code == 422
    assert (
        "incremental" in resp.json()["detail"].lower()
        or "armazenamento" in resp.json()["detail"].lower()
    )


@pytest.mark.asyncio
async def test_trigger_pipeline_default(auth_client_with_doc: AsyncClient):
    auth_client = auth_client_with_doc
    with patch(_START) as mock_start:
        resp = await auth_client.post(f"/api/workspaces/{auth_client.ws_id}/pipeline/run", json={})
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
async def test_trigger_pipeline_from_stage(auth_client_with_doc: AsyncClient):
    auth_client = auth_client_with_doc
    with patch(_START) as mock_start:
        resp = await auth_client.post(
            f"/api/workspaces/{auth_client.ws_id}/pipeline/run",
            json={"from_stage": "E3", "skip_llm": True},
        )
    assert resp.status_code == 202
    args = mock_start.call_args
    stages = args[1]["stages"] if "stages" in args[1] else args.kwargs.get("stages") or args[0][2]
    assert "E3" in stages


@pytest.mark.asyncio
async def test_trigger_pipeline_invalid_from_stage(auth_client: AsyncClient):
    with patch(_START):
        resp = await auth_client.post(
            f"/api/workspaces/{auth_client.ws_id}/pipeline/run", json={"from_stage": "E99"}
        )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_trigger_pipeline_concurrent_blocked(auth_client_with_doc: AsyncClient):
    auth_client = auth_client_with_doc
    with patch(_START):
        resp1 = await auth_client.post(f"/api/workspaces/{auth_client.ws_id}/pipeline/run", json={})
    assert resp1.status_code == 202

    with patch(_START):
        resp2 = await auth_client.post(f"/api/workspaces/{auth_client.ws_id}/pipeline/run", json={})
    assert resp2.status_code == 409
    assert "ativa" in resp2.json()["detail"].lower()


# ---------------------------------------------------------------------------
# List runs
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_runs_empty(auth_client: AsyncClient):
    resp = await auth_client.get(f"/api/workspaces/{auth_client.ws_id}/pipeline/runs")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["runs"] == []


@pytest.mark.asyncio
async def test_list_runs_after_trigger(auth_client_with_doc: AsyncClient):
    auth_client = auth_client_with_doc
    with patch(_START):
        await auth_client.post(f"/api/workspaces/{auth_client.ws_id}/pipeline/run", json={})
    resp = await auth_client.get(f"/api/workspaces/{auth_client.ws_id}/pipeline/runs")
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1


# ---------------------------------------------------------------------------
# Get run detail
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_run_detail(auth_client_with_doc: AsyncClient):
    auth_client = auth_client_with_doc
    with patch(_START):
        trigger_resp = await auth_client.post(
            f"/api/workspaces/{auth_client.ws_id}/pipeline/run", json={}
        )
    run_id = trigger_resp.json()["id"]

    resp = await auth_client.get(f"/api/workspaces/{auth_client.ws_id}/pipeline/runs/{run_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == run_id
    assert "stage_logs" in data


@pytest.mark.asyncio
async def test_get_run_not_found(auth_client: AsyncClient):
    resp = await auth_client.get(f"/api/workspaces/{auth_client.ws_id}/pipeline/runs/nonexistent")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Cancel
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cancel_active_run(auth_client_with_doc: AsyncClient):
    auth_client = auth_client_with_doc
    with patch(_START):
        trigger_resp = await auth_client.post(
            f"/api/workspaces/{auth_client.ws_id}/pipeline/run", json={}
        )
    run_id = trigger_resp.json()["id"]

    with patch(_CANCEL, return_value=True):
        resp = await auth_client.post(
            f"/api/workspaces/{auth_client.ws_id}/pipeline/runs/{run_id}/cancel"
        )
    assert resp.status_code == 200
    assert "cancelamento" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_cancel_not_found(auth_client: AsyncClient):
    with patch(_CANCEL, return_value=False):
        resp = await auth_client.post(
            f"/api/workspaces/{auth_client.ws_id}/pipeline/runs/nonexistent/cancel"
        )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_cancel_already_completed(auth_client_with_doc: AsyncClient):
    auth_client = auth_client_with_doc
    with patch(_START):
        trigger_resp = await auth_client.post(
            f"/api/workspaces/{auth_client.ws_id}/pipeline/run", json={}
        )
    run_id = trigger_resp.json()["id"]

    from backend.app.core.database import get_db
    from backend.app.main import app
    from backend.app.models.pipeline_run import PipelineRunStatus

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
        resp = await auth_client.post(
            f"/api/workspaces/{auth_client.ws_id}/pipeline/runs/{run_id}/cancel"
        )
    assert resp.status_code == 409


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pipeline_unauthorized(client: AsyncClient):
    resp = await client.post(
        "/api/workspaces/00000000-0000-0000-0000-000000000000/pipeline/run", json={}
    )
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_list_runs_unauthorized(client: AsyncClient):
    resp = await client.get("/api/workspaces/00000000-0000-0000-0000-000000000000/pipeline/runs")
    assert resp.status_code in (401, 403)
