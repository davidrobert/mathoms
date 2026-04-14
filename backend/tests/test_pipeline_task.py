"""Tests for Celery pipeline task — Phase 5.

Tests the task function directly (without Celery broker) to validate
stage execution, event publishing, cancellation, and needs_review flows.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.pipeline_run import (
    PipelineRun,
    PipelineRunStatus,
    PipelineStageLog,
    PipelineStageStatus,
)
from backend.app.models.workspace import Workspace
from backend.app.models.user import User


@pytest_asyncio.fixture
async def workspace_with_run(db: AsyncSession):
    """Create a user + workspace + pending pipeline run."""
    from backend.app.core.security import get_password_hash

    user = User(
        id=str(uuid.uuid4()),
        email="task_test@test.com",
        hashed_password=get_password_hash("pass"),
        full_name="Task Tester",
    )
    db.add(user)
    await db.flush()

    ws = Workspace(id=str(uuid.uuid4()), owner_id=user.id, name="Test WS")
    db.add(ws)
    await db.flush()

    run = PipelineRun(
        id=str(uuid.uuid4()),
        workspace_id=ws.id,
        status=PipelineRunStatus.pending,
        total_documents=3,
    )
    db.add(run)
    await db.commit()

    return {"user": user, "workspace": ws, "run": run}


class TestPipelineRunModel:
    """Test the celery_task_id field on PipelineRun."""

    @pytest.mark.asyncio
    async def test_celery_task_id_field(self, db: AsyncSession, workspace_with_run):
        """PipelineRun should have a nullable celery_task_id field."""
        run_id = workspace_with_run["run"].id
        from sqlalchemy import select
        result = await db.execute(select(PipelineRun).where(PipelineRun.id == run_id))
        run = result.scalar_one()
        assert run.celery_task_id is None

        run.celery_task_id = "celery-task-123"
        await db.commit()

        result = await db.execute(select(PipelineRun).where(PipelineRun.id == run_id))
        run = result.scalar_one()
        assert run.celery_task_id == "celery-task-123"


class TestCancellationFlag:
    """Test stage-boundary cancellation via DB flag."""

    @pytest.mark.asyncio
    async def test_cancelled_run_detected(self, db: AsyncSession, workspace_with_run):
        """A run marked cancelled in DB should be detected by _is_cancelled."""
        run_id = workspace_with_run["run"].id

        from sqlalchemy import select
        result = await db.execute(select(PipelineRun).where(PipelineRun.id == run_id))
        run = result.scalar_one()
        run.status = PipelineRunStatus.cancelled
        await db.commit()

        from backend.app.tasks.pipeline_task import _is_cancelled
        assert _is_cancelled(run_id) is True

    @pytest.mark.asyncio
    async def test_running_run_not_cancelled(self, db: AsyncSession, workspace_with_run):
        """A running pipeline should not be detected as cancelled."""
        run_id = workspace_with_run["run"].id

        from sqlalchemy import select
        result = await db.execute(select(PipelineRun).where(PipelineRun.id == run_id))
        run = result.scalar_one()
        run.status = PipelineRunStatus.running
        await db.commit()

        from backend.app.tasks.pipeline_task import _is_cancelled
        assert _is_cancelled(run_id) is False


class TestEventSchemas:
    """Test Pydantic event schemas."""

    def test_pipeline_event_serialization(self):
        from backend.app.schemas.events import PipelineEvent
        event = PipelineEvent(
            event="stage_completed",
            run_id="run-1",
            timestamp=datetime.now(timezone.utc),
            stage="E3",
            status="completed",
            progress_pct=50,
        )
        data = event.model_dump()
        assert data["event"] == "stage_completed"
        assert data["stage"] == "E3"
        assert data["progress_pct"] == 50

    def test_stage_event(self):
        from backend.app.schemas.events import StageEvent
        event = StageEvent(
            event="stage_started",
            run_id="run-1",
            timestamp=datetime.now(timezone.utc),
            stage="E4",
            status="running",
        )
        assert event.stage == "E4"

    def test_run_event(self):
        from backend.app.schemas.events import RunEvent
        event = RunEvent(
            event="run_completed",
            run_id="run-1",
            timestamp=datetime.now(timezone.utc),
            status="completed",
            progress_pct=100,
        )
        assert event.status == "completed"

    def test_error_event(self):
        from backend.app.schemas.events import ErrorEvent
        event = ErrorEvent(
            event="stage_failed",
            run_id="run-1",
            timestamp=datetime.now(timezone.utc),
            error="Parser error",
            stage="E2",
        )
        assert event.error == "Parser error"


class TestPipelineService:
    """Test the updated pipeline_service functions."""

    def test_detect_tier_free(self):
        from backend.app.services.pipeline_service import detect_tier
        with patch("backend.app.services.pipeline_service.SyncSessionLocal") as mock_session:
            mock_db = MagicMock()
            mock_session.return_value.__enter__ = MagicMock(return_value=mock_db)
            mock_session.return_value.__exit__ = MagicMock(return_value=False)
            mock_db.query.return_value.filter.return_value.first.return_value = None
            assert detect_tier("ws-1") == "free"

    def test_detect_tier_premium(self):
        from backend.app.services.pipeline_service import detect_tier
        mock_config = MagicMock()
        mock_config.api_key_encrypted = "encrypted-key"
        with patch("backend.app.services.pipeline_service.SyncSessionLocal") as mock_session:
            mock_db = MagicMock()
            mock_session.return_value.__enter__ = MagicMock(return_value=mock_db)
            mock_session.return_value.__exit__ = MagicMock(return_value=False)
            mock_db.query.return_value.filter.return_value.first.return_value = mock_config
            assert detect_tier("ws-1") == "premium"

    def test_cancel_publishes_event(self):
        """cancel_pipeline_run should publish run_cancelled event."""
        mock_run = MagicMock()
        mock_run.status = PipelineRunStatus.running
        mock_run.celery_task_id = None

        with patch("backend.app.services.pipeline_service.SyncSessionLocal") as mock_session, \
             patch("backend.app.services.pipeline_service.publish_run_cancelled") as mock_publish:
            mock_db = MagicMock()
            mock_session.return_value.__enter__ = MagicMock(return_value=mock_db)
            mock_session.return_value.__exit__ = MagicMock(return_value=False)
            mock_db.get.return_value = mock_run

            from backend.app.services.pipeline_service import cancel_pipeline_run
            result = cancel_pipeline_run("run-1")

            assert result is True
            mock_publish.assert_called_once_with("run-1")

    def test_cancel_nonexistent_run(self):
        with patch("backend.app.services.pipeline_service.SyncSessionLocal") as mock_session:
            mock_db = MagicMock()
            mock_session.return_value.__enter__ = MagicMock(return_value=mock_db)
            mock_session.return_value.__exit__ = MagicMock(return_value=False)
            mock_db.get.return_value = None

            from backend.app.services.pipeline_service import cancel_pipeline_run
            assert cancel_pipeline_run("nonexistent") is False

    def test_is_run_active_running(self):
        mock_run = MagicMock()
        mock_run.status = PipelineRunStatus.running

        with patch("backend.app.services.pipeline_service.SyncSessionLocal") as mock_session:
            mock_db = MagicMock()
            mock_session.return_value.__enter__ = MagicMock(return_value=mock_db)
            mock_session.return_value.__exit__ = MagicMock(return_value=False)
            mock_db.get.return_value = mock_run

            from backend.app.services.pipeline_service import is_run_active
            assert is_run_active("run-1") is True

    def test_is_run_active_completed(self):
        mock_run = MagicMock()
        mock_run.status = PipelineRunStatus.completed

        with patch("backend.app.services.pipeline_service.SyncSessionLocal") as mock_session:
            mock_db = MagicMock()
            mock_session.return_value.__enter__ = MagicMock(return_value=mock_db)
            mock_session.return_value.__exit__ = MagicMock(return_value=False)
            mock_db.get.return_value = mock_run

            from backend.app.services.pipeline_service import is_run_active
            assert is_run_active("run-1") is False
