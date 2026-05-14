"""Phase 5 integration tests — concurrency, cancellation, resume, polling, health check.

Tests the API endpoints with the new Phase 5 behavior.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.models.document import Document, DocumentStatus, DocumentType
from backend.app.models.pipeline_run import (
    PipelineRun,
    PipelineRunStatus,
    PipelineStageLog,
    PipelineStageStatus,
)
from backend.app.models.stage_review import StageReview, StageReviewStatus
from backend.app.models.user import User
from backend.app.models.workspace import Workspace


@pytest_asyncio.fixture
async def auth_user(client: AsyncClient, db: AsyncSession):
    """Register a user and return auth headers + workspace."""
    resp = await client.post(
        "/api/auth/register",
        json={
            "email": "phase5@test.com",
            "password": "testpass123",
            "full_name": "Phase 5 Tester",
        },
    )
    token = resp.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"

    result = await db.execute(select(User).where(User.email == "phase5@test.com"))
    user = result.scalar_one()

    ws_result = await db.execute(select(Workspace).where(Workspace.owner_id == user.id))
    ws = ws_result.scalar_one()

    return {"client": client, "user": user, "workspace": ws}


class TestConcurrencyLimit:
    """5C.1 — 1 pipeline run per workspace, 409 on second."""

    @pytest.mark.asyncio
    async def test_second_run_rejected_when_active(self, auth_user, db: AsyncSession):
        """Starting a second pipeline when one is running should return 409."""
        client = auth_user["client"]
        ws = auth_user["workspace"]

        active_run = PipelineRun(
            id=str(uuid.uuid4()),
            workspace_id=ws.id,
            status=PipelineRunStatus.running,
            total_documents=1,
        )
        db.add(active_run)
        await db.commit()

        resp = await client.post(f"/api/workspaces/{ws.id}/pipeline/run", json={"skip_llm": True})
        assert resp.status_code == 409
        assert (
            "ativa" in resp.json()["detail"].lower() or "execução" in resp.json()["detail"].lower()
        )

    @pytest.mark.asyncio
    async def test_run_allowed_after_completion(self, auth_user, db: AsyncSession):
        """A new run should be allowed after the previous one completes."""
        client = auth_user["client"]
        ws = auth_user["workspace"]

        completed_run = PipelineRun(
            id=str(uuid.uuid4()),
            workspace_id=ws.id,
            status=PipelineRunStatus.completed,
            completed_at=datetime.now(timezone.utc),
            total_documents=1,
        )
        db.add(completed_run)
        # Seed a ready document + a file in the tenant data dir so the
        # endpoint's "no documents to process" gate passes.
        db.add(
            Document(
                workspace_id=ws.id,
                original_name="seed.pdf",
                stored_path=f"/tmp/seed-{ws.id}.pdf",
                doc_type=DocumentType.bank_statement,
                bank_code="itau",
                period="202601",
                status=DocumentStatus.ready,
                file_size_bytes=1,
                content_hash="phase5seed" + ws.id[:22],
            )
        )
        from backend.tests.helpers.if_goal_stub import build_if_goal_stub

        db.add(build_if_goal_stub(ws.id))
        await db.commit()
        data_dir = settings.STORAGE_ROOT / ws.id / "data" / "financial_statements"
        data_dir.mkdir(parents=True, exist_ok=True)
        (data_dir / "seed.pdf").write_bytes(b"x")

        with patch("backend.app.application.pipeline_run.trigger_pipeline.start_pipeline_run"):
            resp = await client.post(
                f"/api/workspaces/{ws.id}/pipeline/run", json={"skip_llm": True}
            )
            assert resp.status_code == 202

    @pytest.mark.asyncio
    async def test_pending_run_blocks_new(self, auth_user, db: AsyncSession):
        """A pending run should also block a new run."""
        client = auth_user["client"]
        ws = auth_user["workspace"]

        pending_run = PipelineRun(
            id=str(uuid.uuid4()),
            workspace_id=ws.id,
            status=PipelineRunStatus.pending,
            total_documents=1,
        )
        db.add(pending_run)
        await db.commit()

        resp = await client.post(f"/api/workspaces/{ws.id}/pipeline/run", json={"skip_llm": True})
        assert resp.status_code == 409


class TestCancellation:
    """5C.2/5C.3 — Stage-boundary cancellation."""

    @pytest.mark.asyncio
    async def test_cancel_running_pipeline(self, auth_user, db: AsyncSession):
        """Cancelling a running pipeline should succeed."""
        client = auth_user["client"]
        ws = auth_user["workspace"]

        run = PipelineRun(
            id=str(uuid.uuid4()),
            workspace_id=ws.id,
            status=PipelineRunStatus.running,
            total_documents=1,
        )
        db.add(run)
        await db.commit()

        with patch("backend.app.services.pipeline_service.publish_run_cancelled") as mock_pub:
            resp = await client.post(f"/api/workspaces/{ws.id}/pipeline/runs/{run.id}/cancel")
            assert resp.status_code == 200
            assert "cancelamento" in resp.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_cancel_completed_pipeline_rejected(self, auth_user, db: AsyncSession):
        """Cancelling a completed pipeline should return 409."""
        client = auth_user["client"]
        ws = auth_user["workspace"]

        run = PipelineRun(
            id=str(uuid.uuid4()),
            workspace_id=ws.id,
            status=PipelineRunStatus.completed,
            completed_at=datetime.now(timezone.utc),
            total_documents=1,
        )
        db.add(run)
        await db.commit()

        resp = await client.post(f"/api/workspaces/{ws.id}/pipeline/runs/{run.id}/cancel")
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_cancel_nonexistent_run(self, auth_user):
        """Cancelling a nonexistent run should return 404."""
        client = auth_user["client"]
        ws = auth_user["workspace"]
        resp = await client.post(f"/api/workspaces/{ws.id}/pipeline/runs/{uuid.uuid4()}/cancel")
        assert resp.status_code == 404


class TestPolling:
    """5B.3 — Polling fallback (GET /api/pipeline/runs/{id})."""

    @pytest.mark.asyncio
    async def test_polling_returns_current_state(self, auth_user, db: AsyncSession):
        """GET /api/pipeline/runs/{id} should return current run state with stage logs."""
        client = auth_user["client"]
        ws = auth_user["workspace"]

        run = PipelineRun(
            id=str(uuid.uuid4()),
            workspace_id=ws.id,
            status=PipelineRunStatus.running,
            current_stage="E3",
            total_documents=5,
            tier_at_run="free",
        )
        db.add(run)
        await db.flush()

        log = PipelineStageLog(
            id=str(uuid.uuid4()),
            pipeline_run_id=run.id,
            stage="E2",
            status=PipelineStageStatus.completed,
            duration_ms=1500,
        )
        db.add(log)
        await db.commit()

        resp = await client.get(f"/api/workspaces/{ws.id}/pipeline/runs/{run.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "running"
        assert data["current_stage"] == "E3"
        assert data["tier_at_run"] == "free"
        assert len(data["stage_logs"]) == 1
        assert data["stage_logs"][0]["stage"] == "E2"
        assert data["stage_logs"][0]["status"] == "completed"

    @pytest.mark.asyncio
    async def test_polling_includes_celery_task_id(self, auth_user, db: AsyncSession):
        """Response should include celery_task_id when present."""
        client = auth_user["client"]
        ws = auth_user["workspace"]

        run = PipelineRun(
            id=str(uuid.uuid4()),
            workspace_id=ws.id,
            status=PipelineRunStatus.running,
            total_documents=1,
            celery_task_id="celery-abc-123",
        )
        db.add(run)
        await db.commit()

        resp = await client.get(f"/api/workspaces/{ws.id}/pipeline/runs/{run.id}")
        assert resp.status_code == 200
        assert resp.json()["celery_task_id"] == "celery-abc-123"

    @pytest.mark.asyncio
    async def test_polling_includes_paused_at_stage(self, auth_user, db: AsyncSession):
        """Response should include paused_at_stage for needs_review runs."""
        client = auth_user["client"]
        ws = auth_user["workspace"]

        run = PipelineRun(
            id=str(uuid.uuid4()),
            workspace_id=ws.id,
            status=PipelineRunStatus.needs_review,
            paused_at_stage="extract_with_llm",
            total_documents=1,
        )
        db.add(run)
        await db.commit()

        resp = await client.get(f"/api/workspaces/{ws.id}/pipeline/runs/{run.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "needs_review"
        assert data["paused_at_stage"] == "extract_with_llm"


class TestResume:
    """5A.7 — Resume after needs_review spawns new task."""

    @pytest.mark.asyncio
    async def test_resume_requires_no_pending_reviews(self, auth_user, db: AsyncSession):
        """Resume should fail if there are still pending reviews."""
        client = auth_user["client"]
        ws = auth_user["workspace"]

        run = PipelineRun(
            id=str(uuid.uuid4()),
            workspace_id=ws.id,
            status=PipelineRunStatus.needs_review,
            paused_at_stage="E1",
            total_documents=1,
        )
        db.add(run)
        await db.flush()

        review = StageReview(
            id=str(uuid.uuid4()),
            pipeline_run_id=run.id,
            stage="E1",
            status=StageReviewStatus.pending,
        )
        db.add(review)
        await db.commit()

        resp = await client.post(f"/api/workspaces/{ws.id}/pipeline/runs/{run.id}/resume")
        assert resp.status_code == 409
        assert "pendentes" in resp.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_resume_not_in_needs_review(self, auth_user, db: AsyncSession):
        """Resume should fail if run is not in needs_review status."""
        client = auth_user["client"]
        ws = auth_user["workspace"]

        run = PipelineRun(
            id=str(uuid.uuid4()),
            workspace_id=ws.id,
            status=PipelineRunStatus.completed,
            total_documents=1,
        )
        db.add(run)
        await db.commit()

        resp = await client.post(f"/api/workspaces/{ws.id}/pipeline/runs/{run.id}/resume")
        assert resp.status_code == 409


class TestRunList:
    """Test listing runs returns all statuses correctly."""

    @pytest.mark.asyncio
    async def test_list_runs_with_new_statuses(self, auth_user, db: AsyncSession):
        """List should include runs with needs_review and resuming statuses."""
        client = auth_user["client"]
        ws = auth_user["workspace"]

        statuses = [
            PipelineRunStatus.completed,
            PipelineRunStatus.needs_review,
            PipelineRunStatus.failed,
        ]
        for s in statuses:
            run = PipelineRun(
                id=str(uuid.uuid4()),
                workspace_id=ws.id,
                status=s,
                total_documents=1,
            )
            db.add(run)
        await db.commit()

        resp = await client.get(f"/api/workspaces/{ws.id}/pipeline/runs")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 3
        found_statuses = {r["status"] for r in data["runs"]}
        assert "needs_review" in found_statuses
        assert "completed" in found_statuses
        assert "failed" in found_statuses


class TestHealthCheck:
    """5A.8 — Health check endpoint."""

    @pytest.mark.asyncio
    async def test_health_returns_component_status(self, client: AsyncClient):
        """Health endpoint should return status for api, redis, celery, database."""
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert "api" in data
        assert data["api"] == "ok"
        assert "version" in data
        # Just check it's a non-empty version string — exact value lives in
        # main.py and is bumped frequently.
        assert isinstance(data["version"], str) and data["version"]
        assert "redis" in data
        assert "celery" in data
        assert "database" in data
        assert "status" in data
        # A6f.1 · ADR-112 — pipeline-service URL + reachability visible even
        # when unset (both None → InProcessPipelineClient in use).
        assert "pipeline_service_url" in data
        assert "pipeline_service_reachable" in data
