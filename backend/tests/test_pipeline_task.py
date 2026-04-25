"""Tests for Celery pipeline task — Phase 5.

Tests the task function directly (without Celery broker) to validate
stage execution, event publishing, cancellation, and needs_review flows.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from unittest.mock import patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.pipeline_run import (
    PipelineRun,
    PipelineRunStatus,
    PipelineStageLog,
    PipelineStageStatus,
)
from backend.app.models.user import User
from backend.app.models.workspace import Workspace
from backend.tests.fakes.fake_sync_session import (
    FakeSyncDbSession,
    FakeSyncSessionFactory,
)


@dataclass
class FakeLLMConfigRow:
    api_key_encrypted: str | None = None


@dataclass
class FakePipelineRunRow:
    status: Any
    celery_task_id: str | None = None
    completed_at: datetime | None = None


async def _build_file_backed_engines(db_file):
    """Async + sync engines compartilhando o mesmo arquivo SQLite (+ metadata)."""
    from sqlalchemy import create_engine
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from sqlalchemy.orm import sessionmaker

    import backend.app.models  # noqa: F401 — register all models on Base
    from backend.app.core.database import Base

    async_engine = create_async_engine(f"sqlite+aiosqlite:///{db_file}")
    sync_engine = create_engine(f"sqlite:///{db_file}")
    async_session = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
    sync_session = sessionmaker(bind=sync_engine, expire_on_commit=False)

    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    return async_engine, sync_engine, async_session, sync_session


async def _seed_pending_run(async_session_factory) -> dict:
    from backend.app.core.security import hash_password

    async with async_session_factory() as session:
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

        return {
            "user_id": user.id,
            "workspace_id": ws.id,
            "run_id": run.id,
            "user": user,
            "workspace": ws,
            "run": run,
        }


@pytest_asyncio.fixture
async def workspace_with_run(tmp_path, monkeypatch, db: AsyncSession):
    """Create user + workspace + pending pipeline run.

    Backed by a temp SQLite FILE (not in-memory) so that the sync
    ``SyncSessionLocal`` used by ``_is_cancelled`` and friends sees the
    same data we write here. The default conftest engine is in-memory
    (``sqlite+aiosqlite://``) which is invisible to a parallel sync
    engine — that's why these tests previously failed.
    """
    import backend.app.tasks.pipeline_task as task_module

    db_file = tmp_path / "pipeline_task.db"
    async_engine, sync_engine, async_session, sync_session = await _build_file_backed_engines(
        db_file
    )
    monkeypatch.setattr(task_module, "SyncSessionLocal", sync_session)

    seeded = await _seed_pending_run(async_session)
    seeded["session"] = async_session

    yield seeded

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

        factory = FakeSyncSessionFactory(FakeSyncDbSession(query_first=None))
        with patch("backend.app.services.pipeline_service.SyncSessionLocal", factory):
            assert detect_tier("ws-1") == "free"

    def test_detect_tier_premium(self):
        from backend.app.services.pipeline_service import detect_tier

        factory = FakeSyncSessionFactory(
            FakeSyncDbSession(query_first=FakeLLMConfigRow(api_key_encrypted="encrypted-key"))
        )
        with (
            patch("backend.app.services.pipeline_service.SyncSessionLocal", factory),
            patch(
                "backend.app.services.pipeline_service._vault.decrypt", return_value="sk-real-key"
            ),
        ):
            assert detect_tier("ws-1") == "premium"

    def test_detect_tier_logs_warning_when_decrypt_returns_none(self, caplog):
        """FERNET_KEY rotacionada → decrypt() retorna None. Silêncio dissimulado
        deixou IRPF sem JSON no prod (2026-04-23): sem log, tier="free" sem rastro.
        """
        import logging as _logging

        from backend.app.services.pipeline_service import detect_tier

        factory = FakeSyncSessionFactory(
            FakeSyncDbSession(query_first=FakeLLMConfigRow(api_key_encrypted="stale-ciphertext"))
        )
        # Isolar de pollution de test ordering: força nível + propagação do logger
        # alvo, caplog propaga o handler na raiz.
        target_logger = _logging.getLogger("backend.app.services.pipeline_service")
        prev_level, prev_prop, prev_disabled = (
            target_logger.level,
            target_logger.propagate,
            target_logger.disabled,
        )
        target_logger.setLevel(_logging.WARNING)
        target_logger.propagate = True
        # alembic's fileConfig (chamado por test_alembic_guardrails) seta
        # disable_existing_loggers=True (default), o que cala este logger
        # em testes rodando depois dele.
        target_logger.disabled = False
        try:
            with (
                patch("backend.app.services.pipeline_service.SyncSessionLocal", factory),
                patch("backend.app.services.pipeline_service._vault.decrypt", return_value=None),
                caplog.at_level(_logging.WARNING),
            ):
                assert detect_tier("ws-1") == "free"
            assert any("decriptou para vazio" in r.getMessage() for r in caplog.records)
        finally:
            target_logger.setLevel(prev_level)
            target_logger.propagate = prev_prop
            target_logger.disabled = prev_disabled

    def test_detect_tier_logs_warning_when_decrypt_raises(self, caplog):
        import logging as _logging

        from backend.app.services.pipeline_service import detect_tier

        factory = FakeSyncSessionFactory(
            FakeSyncDbSession(query_first=FakeLLMConfigRow(api_key_encrypted="stale-ciphertext"))
        )
        target_logger = _logging.getLogger("backend.app.services.pipeline_service")
        prev_level, prev_prop, prev_disabled = (
            target_logger.level,
            target_logger.propagate,
            target_logger.disabled,
        )
        target_logger.setLevel(_logging.WARNING)
        target_logger.propagate = True
        # alembic's fileConfig (chamado por test_alembic_guardrails) seta
        # disable_existing_loggers=True (default), o que cala este logger
        # em testes rodando depois dele.
        target_logger.disabled = False
        try:
            with (
                patch("backend.app.services.pipeline_service.SyncSessionLocal", factory),
                patch(
                    "backend.app.services.pipeline_service._vault.decrypt",
                    side_effect=RuntimeError("invalid token"),
                ),
                caplog.at_level(_logging.WARNING),
            ):
                assert detect_tier("ws-1") == "free"
            assert any("falhou ao decriptar" in r.getMessage() for r in caplog.records)
        finally:
            target_logger.setLevel(prev_level)
            target_logger.propagate = prev_prop
            target_logger.disabled = prev_disabled

    def test_cancel_publishes_event(self):
        """cancel_pipeline_run should publish run_cancelled event."""
        run_row = FakePipelineRunRow(status=PipelineRunStatus.running, celery_task_id=None)
        factory = FakeSyncSessionFactory(FakeSyncDbSession(get_result=run_row))

        with (
            patch("backend.app.services.pipeline_service.SyncSessionLocal", factory),
            patch("backend.app.services.pipeline_service.publish_run_cancelled") as mock_publish,
        ):
            from backend.app.services.pipeline_service import cancel_pipeline_run

            result = cancel_pipeline_run("run-1")

            assert result is True
            mock_publish.assert_called_once_with("run-1")

    def test_cancel_nonexistent_run(self):
        factory = FakeSyncSessionFactory(FakeSyncDbSession(get_result=None))
        with patch("backend.app.services.pipeline_service.SyncSessionLocal", factory):
            from backend.app.services.pipeline_service import cancel_pipeline_run

            assert cancel_pipeline_run("nonexistent") is False

    def test_is_run_active_running(self):
        run_row = FakePipelineRunRow(status=PipelineRunStatus.running)
        factory = FakeSyncSessionFactory(FakeSyncDbSession(get_result=run_row))
        with patch("backend.app.services.pipeline_service.SyncSessionLocal", factory):
            from backend.app.services.pipeline_service import is_run_active

            assert is_run_active("run-1") is True

    def test_is_run_active_completed(self):
        run_row = FakePipelineRunRow(status=PipelineRunStatus.completed)
        factory = FakeSyncSessionFactory(FakeSyncDbSession(get_result=run_row))
        with patch("backend.app.services.pipeline_service.SyncSessionLocal", factory):
            from backend.app.services.pipeline_service import is_run_active

            assert is_run_active("run-1") is False


class TestCreateReportFromOutput:
    """ADR-131: Report é criado com FK ao pipeline_artifact E5; o disco
    deixou de ser fonte de verdade."""

    @pytest.mark.asyncio
    async def test_creates_report_with_artifact_fk(self, workspace_with_run, tmp_path):
        """Com artefato no DB, cria Report apontando para a row via FK."""
        from sqlalchemy import select

        from backend.app.models.pipeline_artifact import PipelineArtifact
        from backend.app.models.report import Report
        from backend.app.tasks.pipeline_task import _create_report_from_output

        ws_id = workspace_with_run["workspace_id"]
        run_id = workspace_with_run["run_id"]
        Session = workspace_with_run["session"]

        payload = {
            "score": {"valor": 7.5, "classificacao": "bom"},
            "ratios": {"taxa_poupanca_recorrente_pct": 22.5},
            "patrimonio": {"bruto": 1000.0, "investivel": 800.0},
            "goals": {"if_meta": 5000.0, "if_pct": 16.0, "prazo_anos_realista": 10},
        }
        async with Session() as db:
            artifact = PipelineArtifact(
                workspace_id=ws_id,
                pipeline_run_id=run_id,
                stage="E5",
                artifact_key="analise_financeira",
                content_json=payload,
            )
            db.add(artifact)
            await db.commit()
            artifact_id = artifact.id

        _create_report_from_output(ws_id, run_id, tmp_path / "tenant")

        async with Session() as db:
            result = await db.execute(select(Report).where(Report.workspace_id == ws_id))
            reports = result.scalars().all()
            assert len(reports) == 1
            assert reports[0].pipeline_run_id == run_id
            assert reports[0].analysis_artifact_id == artifact_id

    @pytest.mark.asyncio
    async def test_no_artifact_no_report(self, workspace_with_run, tmp_path, caplog):
        """Sem artefato no DB → não cria report e loga error."""
        import logging as _logging

        from sqlalchemy import select

        from backend.app.models.report import Report
        from backend.app.tasks.pipeline_task import _create_report_from_output

        ws_id = workspace_with_run["workspace_id"]
        run_id = workspace_with_run["run_id"]
        Session = workspace_with_run["session"]

        tenant_root = tmp_path / "tenant"
        # alembic's fileConfig (chamado por test_alembic_guardrails) seta
        # disable_existing_loggers=True (default), o que cala este logger
        # em testes rodando depois dele. Mesmo workaround dos testes de tier.
        target_logger = _logging.getLogger("backend.app.tasks.pipeline_task")
        prev_level, prev_prop, prev_disabled = (
            target_logger.level,
            target_logger.propagate,
            target_logger.disabled,
        )
        target_logger.setLevel(_logging.ERROR)
        target_logger.propagate = True
        target_logger.disabled = False
        try:
            with caplog.at_level(_logging.ERROR, logger="backend.app.tasks.pipeline_task"):
                _create_report_from_output(ws_id, run_id, tenant_root)
            assert any("report_creation_skipped" in r.getMessage() for r in caplog.records)
        finally:
            target_logger.setLevel(prev_level)
            target_logger.propagate = prev_prop
            target_logger.disabled = prev_disabled

        async with Session() as db:
            result = await db.execute(select(Report).where(Report.workspace_id == ws_id))
            assert result.scalars().all() == []
