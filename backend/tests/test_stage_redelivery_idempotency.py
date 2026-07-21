"""A37.l12 (EXEC-01) — idempotência de redelivery por marcador de conclusão de stage.

Redelivery Celery (``acks_late``; crash/sleep do host) re-executa
``pipeline.run`` do zero. Sem guard, stage LLM já concluído re-paga a call
e duplica rows em ``pipeline_stage_logs``. O guard checa o stage_log
terminal por ``(run_id, stage)`` — não "artifact existe", que não cobre
redelivery mid-stage antes do write — e pula reusando os artefatos, com
``redelivered=true`` na telemetria.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

import pytest
import pytest_asyncio
from sqlalchemy import select

from backend.app.core.security import hash_password
from backend.app.models.pipeline_artifact import PipelineArtifact
from backend.app.models.pipeline_run import (
    PipelineRun,
    PipelineRunStatus,
    PipelineStageLog,
    PipelineStageStatus,
)
from backend.app.models.user import User
from backend.app.models.workspace import Workspace
from backend.tests.test_pipeline_task import _build_file_backed_engines
from pipeline.orchestrator import StageResult


class _CountingStage:
    """Fake LLM client — conta chamadas por stage (critério: zero call nova)."""

    def __init__(self, fail_stages: set[str] | None = None):
        self.calls: list[str] = []
        self._fail_stages = fail_stages or set()

    def __call__(self, ctx, stage):
        self.calls.append(stage)
        if stage in self._fail_stages:
            raise RuntimeError(f"boom em {stage}")
        ctx.artifact_store.write(stage, "members", {"calls": len(self.calls)})
        return StageResult(stage=stage, success=True, duration_ms=1.0, detail={"ok": True})

    def count_for(self, stage: str) -> int:
        return sum(1 for s in self.calls if s == stage)


def _make_user_row() -> User:
    return User(
        id=str(uuid.uuid4()),
        email=f"redelivery_{uuid.uuid4().hex[:6]}@test.com",
        hashed_password=hash_password("pass"),
        full_name="RedeliveryTest",
    )


async def _seed_workspace_and_run(async_session_factory) -> dict:
    async with async_session_factory() as session:
        user = _make_user_row()
        ws = Workspace(id=str(uuid.uuid4()), owner_id=user.id, name="WS")
        run = PipelineRun(
            id=str(uuid.uuid4()),
            workspace_id=ws.id,
            status=PipelineRunStatus.running,
            total_documents=2,
        )
        session.add_all([user, ws, run])
        await session.commit()
        return {"ws_id": ws.id, "run_id": run.id}


@pytest_asyncio.fixture
async def seeded_run(tmp_path):
    import backend.app.tasks.pipeline_task as task_module

    db_file = tmp_path / "redelivery.db"
    async_engine, sync_engine, async_session, sync_session = await _build_file_backed_engines(
        db_file
    )
    seed = await _seed_workspace_and_run(async_session)
    seed["async_session"] = async_session

    with patch.object(task_module, "SyncSessionLocal", sync_session):
        yield seed

    await async_engine.dispose()
    sync_engine.dispose()


def _run_loop(seed, stage_fn, *, stages=None, skip_llm=False, llm_stages=None):
    from backend.app.tasks.pipeline_task import _execute_stages_loop

    return _execute_stages_loop(
        SimpleNamespace(artifact_store=None),
        stages=stages or ["extract_members"],
        run_id=seed["run_id"],
        ws_id=seed["ws_id"],
        skip_llm=skip_llm,
        stop_on_error=True,
        tier="premium",
        llm_stages=llm_stages or set(),
        run_stage_fn=stage_fn,
    )


async def _stage_logs(seed, stage: str) -> list[PipelineStageLog]:
    async with seed["async_session"]() as session:
        return list(
            (
                await session.execute(
                    select(PipelineStageLog).where(
                        PipelineStageLog.pipeline_run_id == seed["run_id"],
                        PipelineStageLog.stage == stage,
                    )
                )
            )
            .scalars()
            .all()
        )


async def _artifact_snapshot(seed) -> dict:
    async with seed["async_session"]() as session:
        rows = (
            (
                await session.execute(
                    select(PipelineArtifact).where(
                        PipelineArtifact.pipeline_run_id == seed["run_id"]
                    )
                )
            )
            .scalars()
            .all()
        )
        return {(a.stage, a.artifact_key): a.content_json for a in rows}


async def _seed_running_stage_log(seed, stage: str) -> None:
    async with seed["async_session"]() as session:
        session.add(
            PipelineStageLog(
                id=str(uuid.uuid4()),
                pipeline_run_id=seed["run_id"],
                stage=stage,
                status=PipelineStageStatus.running,
                started_at=datetime.now(timezone.utc),
            )
        )
        await session.commit()


@pytest.mark.asyncio
async def test_redelivery_skips_completed_stage_zero_new_llm_calls(seeded_run):
    """Stage concluído + redelivery → zero call LLM nova, artifacts inalterados,
    sem stage_log duplicado, ``redelivered=true`` na telemetria."""
    stage_fn = _CountingStage()

    has_failure, _ = _run_loop(seeded_run, stage_fn)
    assert not has_failure
    assert stage_fn.count_for("extract_members") == 1
    artifacts_before = await _artifact_snapshot(seeded_run)

    # Redelivery: mesma task, mesmos args, re-executa o loop do zero.
    has_failure, _ = _run_loop(seeded_run, stage_fn)
    assert not has_failure

    assert stage_fn.count_for("extract_members") == 1  # zero call nova
    logs = await _stage_logs(seeded_run, "extract_members")
    assert len(logs) == 1  # sem row duplicada
    assert logs[0].status == PipelineStageStatus.completed
    assert logs[0].output_summary.get("redelivered") is True
    assert await _artifact_snapshot(seeded_run) == artifacts_before


@pytest.mark.asyncio
async def test_redelivery_reexecutes_stage_interrupted_mid_stage(seeded_run):
    """Crash mid-stage (log ``running``, sem marcador terminal) → re-executa.
    "Artifact existe" não serviria: aqui não há artifact E não há marcador."""
    await _seed_running_stage_log(seeded_run, "extract_members")

    stage_fn = _CountingStage()
    has_failure, _ = _run_loop(seeded_run, stage_fn)

    assert not has_failure
    assert stage_fn.count_for("extract_members") == 1
    statuses = {log.status for log in await _stage_logs(seeded_run, "extract_members")}
    assert PipelineStageStatus.completed in statuses


@pytest.mark.asyncio
async def test_redelivery_does_not_duplicate_skip_rows(seeded_run):
    """Stage pulado (skip_llm) também é marcador — redelivery não duplica a row."""
    stage_fn = _CountingStage()
    kwargs = {"skip_llm": True, "llm_stages": {"extract_members"}}

    _run_loop(seeded_run, stage_fn, **kwargs)
    _run_loop(seeded_run, stage_fn, **kwargs)

    assert stage_fn.count_for("extract_members") == 0
    logs = await _stage_logs(seeded_run, "extract_members")
    assert len(logs) == 1
    assert logs[0].status == PipelineStageStatus.skipped


@pytest.mark.asyncio
async def test_redelivery_resumes_from_first_unfinished_stage(seeded_run):
    """Run parcial (stage 1 ok, stage 2 crashou) → redelivery pula o 1 e
    re-executa só o 2."""
    first = _CountingStage(fail_stages={"extract_baseline"})
    has_failure, _ = _run_loop(seeded_run, first, stages=["extract_members", "extract_baseline"])
    assert has_failure
    assert first.count_for("extract_members") == 1

    second = _CountingStage()
    has_failure, _ = _run_loop(seeded_run, second, stages=["extract_members", "extract_baseline"])

    assert not has_failure
    assert second.count_for("extract_members") == 0  # reusado, zero call nova
    assert second.count_for("extract_baseline") == 1  # re-executado
