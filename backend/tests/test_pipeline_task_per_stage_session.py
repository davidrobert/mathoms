"""Regression test — artifact session é por-stage (2026-04-23 lock incident).

Incidente: ``sqlite3.OperationalError: database is locked`` no Celery
quando a sessão do ``DBArtifactStore`` ficava aberta pela run inteira,
competindo com a sessão que grava em ``pipeline_stage_logs``.

Mitigação #3: ``_execute_stages_loop`` abre uma sessão fresca +
``DBArtifactStore`` por stage e fecha após cada commit/rollback.

Este teste valida exatamente isso: com 2 stages, duas sessões distintas
são abertas, e **ambas** são fechadas antes do loop terminar.
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import patch

import pytest
import pytest_asyncio

from backend.app.core.security import hash_password
from backend.app.models.pipeline_run import PipelineRun, PipelineRunStatus
from backend.app.models.user import User
from backend.app.models.workspace import Workspace
from backend.tests.test_pipeline_task import _build_file_backed_engines
from pipeline.orchestrator import StageResult


class _SessionTracker:
    """Envolve o factory SyncSessionLocal real e registra cada sessão criada.

    Cada sessão fica guardada em ``self.sessions`` com flag ``closed`` que
    vira ``True`` quando ``close()`` é chamado.
    """

    def __init__(self, real_factory):
        self._real = real_factory
        self.sessions: list = []

    def __call__(self):
        sess = self._real()
        self.sessions.append(sess)
        orig_close = sess.close
        sess.closed_flag = False

        def _tracked_close():
            sess.closed_flag = True
            orig_close()

        sess.close = _tracked_close
        return sess


async def _seed_workspace_and_run(async_session_factory) -> dict:
    async with async_session_factory() as session:
        user = User(
            id=str(uuid.uuid4()),
            email=f"stage_session_{uuid.uuid4().hex[:6]}@test.com",
            hashed_password=hash_password("pass"),
            full_name="SessionTest",
        )
        session.add(user)
        await session.flush()

        ws = Workspace(id=str(uuid.uuid4()), owner_id=user.id, name="WS")
        session.add(ws)
        await session.flush()

        run = PipelineRun(
            id=str(uuid.uuid4()),
            workspace_id=ws.id,
            status=PipelineRunStatus.running,
            total_documents=2,
        )
        session.add(run)
        await session.commit()

        return {"ws_id": ws.id, "run_id": run.id}


@pytest_asyncio.fixture
async def seeded_run(tmp_path):
    import backend.app.tasks.pipeline_task as task_module

    db_file = tmp_path / "per_stage_session.db"
    async_engine, sync_engine, async_session, sync_session = await _build_file_backed_engines(
        db_file
    )
    tracker = _SessionTracker(sync_session)

    seed = await _seed_workspace_and_run(async_session)
    seed["tracker"] = tracker
    seed["task_module"] = task_module
    seed["real_sync_session"] = sync_session

    with patch.object(task_module, "SyncSessionLocal", tracker):
        yield seed

    await async_engine.dispose()
    sync_engine.dispose()


@pytest.mark.asyncio
async def test_artifact_session_opens_and_closes_per_stage(seeded_run):
    """2 stages → 2 sessões artifact distintas, ambas fechadas antes do loop
    terminar.

    Sem o fix, apenas 1 sessão seria criada no setup e mantida aberta —
    bloqueando writes concorrentes em ``pipeline_stage_logs``.

    ADR-212 PR3a: ``DBArtifactStore`` é sempre o store; flag
    ``use_db_artifacts`` removida.
    """
    from backend.app.tasks.pipeline_task import _execute_stages_loop

    tracker = seeded_run["tracker"]
    ws_id = seeded_run["ws_id"]
    run_id = seeded_run["run_id"]

    ctx = SimpleNamespace(artifact_store=None)

    def _fake_run_stage(_ctx, stage):
        # Sanity: a cada stage, ctx.artifact_store deve ser um DBArtifactStore
        # novo (sessão fresca).
        assert _ctx.artifact_store is not None, f"no store injected for stage={stage}"
        return StageResult(stage=stage, success=True, duration_ms=1.0, detail={})

    has_failure, paused = _execute_stages_loop(
        ctx,
        stages=["E2", "E3"],
        run_id=run_id,
        ws_id=ws_id,
        skip_llm=False,
        stop_on_error=True,
        tier="free",
        llm_stages=set(),
        run_stage_fn=_fake_run_stage,
    )

    assert not has_failure
    assert not paused

    # Filtra apenas as sessões do artifact store. O loop também abre
    # sessões para _record_stage_running / _record_stage_result — todas
    # devem estar fechadas, mas pelo menos 2 pertencem ao artifact store
    # (uma por stage). Checagem simples: TODAS as sessões rastreadas
    # precisam estar fechadas.
    assert len(tracker.sessions) >= 2, f"esperava >= 2 sessões, vi {len(tracker.sessions)}"
    unclosed = [s for s in tracker.sessions if not getattr(s, "closed_flag", False)]
    assert not unclosed, f"{len(unclosed)} sessões ficaram abertas após o loop"


@pytest.mark.asyncio
async def test_artifact_session_closed_on_stage_failure(seeded_run):
    """Stage falha (exception) → rollback + close da sessão artifact."""
    from backend.app.tasks.pipeline_task import _execute_stages_loop

    tracker = seeded_run["tracker"]

    def _failing_stage(_ctx, stage):
        raise RuntimeError("boom")

    has_failure, paused = _execute_stages_loop(
        ctx=SimpleNamespace(artifact_store=None),
        stages=["E2"],
        run_id=seeded_run["run_id"],
        ws_id=seeded_run["ws_id"],
        skip_llm=False,
        stop_on_error=True,
        tier="free",
        llm_stages=set(),
        run_stage_fn=_failing_stage,
    )

    assert has_failure
    assert not paused
    unclosed = [s for s in tracker.sessions if not getattr(s, "closed_flag", False)]
    assert not unclosed, "sessão artifact deve ser fechada mesmo quando stage falha"


# Test legado ``test_no_artifact_session_when_flag_disabled`` removido em
# ADR-212 PR3a — flag ``use_db_artifacts`` foi descontinuada e o caminho
# disco deixou de ser opt-out runtime.
