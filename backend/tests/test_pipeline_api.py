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
    # F9.2: from_stage="E3" (legado) resolve para "reconcile_transactions" (descritivo).
    assert "reconcile_transactions" in stages


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


# ---------------------------------------------------------------------------
# ADR-291 — from_stage exige run base coerente (fallback pinado)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_trigger_from_stage_e4_without_prior_run_returns_422(
    auth_client_with_doc: AsyncClient,
):
    """Sem run anterior com E3, from_stage=E4 falha alto — nunca relatório zerado."""
    auth_client = auth_client_with_doc
    with patch(_START) as mock_start:
        resp = await auth_client.post(
            f"/api/workspaces/{auth_client.ws_id}/pipeline/run",
            json={"from_stage": "E4", "skip_llm": True},
        )
    assert resp.status_code == 422
    assert "pipeline completo" in resp.json()["detail"]
    mock_start.assert_not_called()


@pytest.mark.asyncio
async def test_trigger_from_stage_e4_pins_base_run_with_e3(
    auth_client_with_doc: AsyncClient, db: AsyncSession
):
    """Com run anterior contendo E3, from_stage=E4 pina o base_run e propaga o fallback."""
    from backend.app.models.pipeline_artifact import PipelineArtifact
    from backend.app.models.pipeline_run import PipelineRun, PipelineRunStatus

    auth_client = auth_client_with_doc
    ws_id = auth_client.ws_id

    prior = PipelineRun(workspace_id=ws_id, status=PipelineRunStatus.completed)
    db.add(prior)
    await db.flush()
    db.add(
        PipelineArtifact(
            workspace_id=ws_id,
            pipeline_run_id=prior.id,
            stage="E3",
            artifact_key="itau_extratoconta_BRL_202601_202604",
            content_json={"transacoes": [{"v": 1}]},
        )
    )
    await db.commit()
    prior_id = prior.id

    with patch(_START) as mock_start:
        resp = await auth_client.post(
            f"/api/workspaces/{ws_id}/pipeline/run",
            json={"from_stage": "E4", "skip_llm": True},
        )
    assert resp.status_code == 202
    kwargs = mock_start.call_args.kwargs
    assert kwargs["base_run_id"] == prior_id
    assert "E3" in kwargs["base_run_fallback_stages"]
    assert "reconcile_transactions" in kwargs["base_run_fallback_stages"]
    # E4/E5 são recomputados no run novo — não entram no fallback.
    assert "E4" not in kwargs["base_run_fallback_stages"]

    run_id = resp.json()["id"]
    created = await db.get(PipelineRun, run_id)
    assert created.base_run_id == prior_id


@pytest.mark.asyncio
async def test_trigger_from_stage_e5_requires_e3_and_e4_superset(
    auth_client_with_doc: AsyncClient, db: AsyncSession
):
    """from_stage=E5 lê E3 E E4 — run com só E3 não qualifica como base (pin único, ADR-291)."""
    from backend.app.models.pipeline_artifact import PipelineArtifact
    from backend.app.models.pipeline_run import PipelineRun, PipelineRunStatus

    auth_client = auth_client_with_doc
    ws_id = auth_client.ws_id

    only_e3 = PipelineRun(workspace_id=ws_id, status=PipelineRunStatus.failed)
    db.add(only_e3)
    await db.flush()
    db.add(
        PipelineArtifact(
            workspace_id=ws_id,
            pipeline_run_id=only_e3.id,
            stage="E3",
            artifact_key="itau_x",
            content_json={"transacoes": []},
        )
    )
    await db.commit()

    with patch(_START) as mock_start:
        resp = await auth_client.post(
            f"/api/workspaces/{ws_id}/pipeline/run",
            json={"from_stage": "E5", "skip_llm": True},
        )
    assert resp.status_code == 422
    mock_start.assert_not_called()

    full = PipelineRun(workspace_id=ws_id, status=PipelineRunStatus.completed)
    db.add(full)
    await db.flush()
    for stage, key in (("E3", "itau_x"), ("E4", "despesas")):
        db.add(
            PipelineArtifact(
                workspace_id=ws_id,
                pipeline_run_id=full.id,
                stage=stage,
                artifact_key=key,
                content_json={},
            )
        )
    await db.commit()
    full_id = full.id

    with patch(_START) as mock_start:
        resp = await auth_client.post(
            f"/api/workspaces/{ws_id}/pipeline/run",
            json={"from_stage": "E5", "skip_llm": True},
        )
    assert resp.status_code == 202
    kwargs = mock_start.call_args.kwargs
    assert kwargs["base_run_id"] == full_id
    assert {"E3", "E4"} <= set(kwargs["base_run_fallback_stages"])


async def _add_failed_run_with_e5(db: AsyncSession, ws_id: str) -> str:
    """Run falhado com artifact E5 — base mínima p/ from_stage=parecer (ADR-291)."""
    from backend.app.models.pipeline_artifact import PipelineArtifact
    from backend.app.models.pipeline_run import PipelineRun, PipelineRunStatus

    prior = PipelineRun(workspace_id=ws_id, status=PipelineRunStatus.failed)
    db.add(prior)
    await db.flush()
    db.add(
        PipelineArtifact(
            workspace_id=ws_id,
            pipeline_run_id=prior.id,
            stage="E5",
            artifact_key="analise_financeira",
            content_json={},
        )
    )
    await db.commit()
    return prior.id


@pytest.mark.asyncio
async def test_trigger_from_stage_descriptive_name_accepted(
    auth_client_with_doc: AsyncClient, db: AsyncSession
):
    """from_stage descritivo (``failed_at_stage`` pós-F9.2) é aceito — o botão
    "Reprocessar a partir de <stage>" da UI envia o nome descritivo, e o set
    legado hardcoded devolvia 422 (incidente parecer 2026-06-12)."""
    auth_client = auth_client_with_doc
    prior_id = await _add_failed_run_with_e5(db, auth_client.ws_id)

    with patch(_START) as mock_start:
        resp = await auth_client.post(
            f"/api/workspaces/{auth_client.ws_id}/pipeline/run",
            json={"from_stage": "review_finances_holistic", "skip_llm": False},
        )
    assert resp.status_code == 202
    kwargs = mock_start.call_args.kwargs
    assert kwargs["stages"] == ["review_finances_holistic"]
    assert kwargs["base_run_id"] == prior_id


@pytest.mark.asyncio
async def test_trigger_from_stage_e3_does_not_pin_base_run(
    auth_client_with_doc: AsyncClient,
):
    """from_stage=E3 lê só E2 (workspace-scoped, ADR-241) — sem base_run, sem 422."""
    auth_client = auth_client_with_doc
    with patch(_START) as mock_start:
        resp = await auth_client.post(
            f"/api/workspaces/{auth_client.ws_id}/pipeline/run",
            json={"from_stage": "E3", "skip_llm": True},
        )
    assert resp.status_code == 202
    kwargs = mock_start.call_args.kwargs
    assert kwargs["base_run_id"] is None
    assert kwargs["base_run_fallback_stages"] == []
