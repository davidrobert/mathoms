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
async def workspace_with_run(tmp_path, monkeypatch, db: AsyncSession):
    """Create user + workspace + pending pipeline run.

    Backed by a temp SQLite FILE (not in-memory) so that the sync
    ``SyncSessionLocal`` used by ``_is_cancelled`` and friends sees the
    same data we write here. The default conftest engine is in-memory
    (``sqlite+aiosqlite://``) which is invisible to a parallel sync
    engine — that's why these tests previously failed.
    """
    from sqlalchemy import create_engine
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    from sqlalchemy.orm import sessionmaker

    from backend.app.core.database import Base
    from backend.app.core.security import hash_password
    import backend.app.models  # noqa: F401 — register all models on Base
    import backend.app.tasks.pipeline_task as task_module

    db_file = tmp_path / "pipeline_task.db"
    async_url = f"sqlite+aiosqlite:///{db_file}"
    sync_url = f"sqlite:///{db_file}"

    async_engine = create_async_engine(async_url)
    sync_engine = create_engine(sync_url)
    AsyncTestSession = async_sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )
    SyncTestSession = sessionmaker(bind=sync_engine, expire_on_commit=False)

    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    monkeypatch.setattr(task_module, "SyncSessionLocal", SyncTestSession)

    async with AsyncTestSession() as session:
        user = User(
            id=str(uuid.uuid4()),
            email="task_test@test.com",
            hashed_password=hash_password("pass"),
            full_name="Task Tester",
        )
        session.add(user)
        await session.flush()

        ws = Workspace(id=str(uuid.uuid4()), owner_id=user.id, name="Test WS")
        session.add(ws)
        await session.flush()

        run = PipelineRun(
            id=str(uuid.uuid4()),
            workspace_id=ws.id,
            status=PipelineRunStatus.pending,
            total_documents=3,
        )
        session.add(run)
        await session.commit()

        # Re-attach to the conftest db session so existing tests that read
        # the run via the ``db`` fixture keep working.
        # We use the IDs only — actual reads happen against AsyncTestSession.
        result = {
            "user_id": user.id, "workspace_id": ws.id, "run_id": run.id,
            "session": AsyncTestSession,
            "user": user, "workspace": ws, "run": run,
        }

    yield result

    await async_engine.dispose()
    sync_engine.dispose()


class TestPipelineRunModel:
    """Test the celery_task_id field on PipelineRun."""

    @pytest.mark.asyncio
    async def test_celery_task_id_field(self, workspace_with_run):
        """PipelineRun should have a nullable celery_task_id field."""
        run_id = workspace_with_run["run_id"]
        Session = workspace_with_run["session"]
        from sqlalchemy import select
        async with Session() as db:
            result = await db.execute(select(PipelineRun).where(PipelineRun.id == run_id))
            run = result.scalar_one()
            assert run.celery_task_id is None

            run.celery_task_id = "celery-task-123"
            await db.commit()

        async with Session() as db:
            result = await db.execute(select(PipelineRun).where(PipelineRun.id == run_id))
            run = result.scalar_one()
            assert run.celery_task_id == "celery-task-123"


class TestCancellationFlag:
    """Test stage-boundary cancellation via DB flag."""

    @pytest.mark.asyncio
    async def test_cancelled_run_detected(self, workspace_with_run):
        """A run marked cancelled in DB should be detected by _is_cancelled."""
        run_id = workspace_with_run["run_id"]
        Session = workspace_with_run["session"]

        from sqlalchemy import select
        async with Session() as db:
            result = await db.execute(select(PipelineRun).where(PipelineRun.id == run_id))
            run = result.scalar_one()
            run.status = PipelineRunStatus.cancelled
            await db.commit()

        from backend.app.tasks.pipeline_task import _is_cancelled
        assert _is_cancelled(run_id) is True

    @pytest.mark.asyncio
    async def test_running_run_not_cancelled(self, workspace_with_run):
        """A running pipeline should not be detected as cancelled."""
        run_id = workspace_with_run["run_id"]
        Session = workspace_with_run["session"]

        from sqlalchemy import select
        async with Session() as db:
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
        with patch("backend.app.services.pipeline_service.SyncSessionLocal") as mock_session, patch(
            "backend.app.services.pipeline_service._vault.decrypt", return_value="sk-real-key"
        ):
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
