"""ADR-359 — falha de dispatch é alta e o caller compensa o estado que criou.

Cada teste pina uma afirmação da decisão, não a implementação. O caso de origem:
`make pipeline-run` com Redis fora retornava exit 0 e deixava o run `pending`
para sempre, trancando o workspace via `ux_pipeline_runs_ws_active`.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.pipeline_run import PipelineRun, PipelineRunStatus
from backend.app.services.pipeline.pipeline_failure_reasons import (
    DISPATCH_FAILED,
    DISPATCH_UNCONFIRMED,
    RUN_SETUP_FAILED,
)
from backend.app.services.pipeline.pipeline_service import PipelineDispatchError

_START = "backend.app.application.pipeline_run.trigger_pipeline.start_pipeline_run"
_PREPARE = "backend.app.services.pipeline.pipeline_service._prepare_run_context"
_DISPATCH = "backend.app.services.pipeline.pipeline_service._dispatch_celery_task"


async def _latest_run(ws_id: str, db: AsyncSession) -> PipelineRun:
    result = await db.execute(
        select(PipelineRun)
        .where(PipelineRun.workspace_id == ws_id)
        .order_by(PipelineRun.started_at.desc())
        .limit(1)
    )
    return result.scalars().first()


async def _trigger(auth_client: AsyncClient) -> int:
    resp = await auth_client.post(f"/api/workspaces/{auth_client.ws_id}/pipeline/run", json={})
    return resp.status_code


@pytest.mark.asyncio
async def test_dispatch_failure_marks_run_failed_and_unblocks_workspace(
    auth_client_with_doc: AsyncClient, db: AsyncSession
):
    """503 + run `failed` + workspace liberado — tudo sem Redis, no mesmo request."""
    auth_client = auth_client_with_doc
    with patch(_START, side_effect=PipelineDispatchError(DISPATCH_FAILED, "run-x")):
        status = await _trigger(auth_client)
    assert status == 503

    run = await _latest_run(auth_client.ws_id, db)
    assert run.status == PipelineRunStatus.failed
    assert run.failure_reason == DISPATCH_FAILED
    assert run.completed_at is not None

    # O sintoma reportado era exatamente este: o segundo disparo ficava travado.
    with patch(_START):
        assert await _trigger(auth_client) == 202


@pytest.mark.asyncio
async def test_run_setup_failure_uses_its_own_reason(
    auth_client_with_doc: AsyncClient, db: AsyncSession
):
    """`_prepare_run_context` falha por outra porta e produz o mesmo órfão."""
    auth_client = auth_client_with_doc
    with patch(_START, side_effect=PipelineDispatchError(RUN_SETUP_FAILED, "run-x")):
        assert await _trigger(auth_client) == 503

    run = await _latest_run(auth_client.ws_id, db)
    assert run.failure_reason == RUN_SETUP_FAILED


def _claim_then_fail(**kwargs):
    """Simula enqueue bem-sucedido cujo ack falhou: o worker já reivindicou o run."""
    from backend.app.core.database import SyncSessionLocal

    with SyncSessionLocal() as sync_db:
        run = sync_db.get(PipelineRun, kwargs["run_id"])
        run.status = PipelineRunStatus.running
        sync_db.commit()
    raise PipelineDispatchError(DISPATCH_FAILED, kwargs["run_id"])


# Sem o filtro por `status='pending'` a compensação liberaria o workspace com a
# task viva, e dois workers escreveriam artefatos do mesmo workspace.
@pytest.mark.asyncio
async def test_compensation_is_noop_when_worker_already_claimed_the_run(
    auth_client_with_doc: AsyncClient, db: AsyncSession
):
    """Enqueue publicou, ack falhou: a task ESTÁ na fila."""
    auth_client = auth_client_with_doc
    with patch(_START, side_effect=_claim_then_fail):
        assert await _trigger(auth_client) == 503

    run = await _latest_run(auth_client.ws_id, db)
    await db.refresh(run)
    assert run.status == PipelineRunStatus.running
    assert run.failure_reason is None


@pytest.mark.asyncio
async def test_undispatched_orphan_is_healed_at_the_blocking_point(
    auth_client_with_doc: AsyncClient, db: AsyncSession
):
    """Órfão sem `celery_task_id` mais velho que o threshold não tranca o workspace."""
    auth_client = auth_client_with_doc
    with patch(_START):
        assert await _trigger(auth_client) == 202

    run = await _latest_run(auth_client.ws_id, db)
    run.started_at = datetime.now(timezone.utc) - timedelta(minutes=30)
    run.celery_task_id = None
    await db.commit()

    with patch(_START):
        assert await _trigger(auth_client) == 202

    await db.refresh(run)
    assert run.status == PipelineRunStatus.failed
    assert run.failure_reason == DISPATCH_UNCONFIRMED


# É o invariante que a pré-geração do task_id compra: sem ele, run legítimo
# esperando fila seria marcado `failed` e depois recusado pelo worker.
@pytest.mark.asyncio
async def test_queued_run_is_never_healed(auth_client_with_doc: AsyncClient, db: AsyncSession):
    """Com `celery_task_id` gravado a task está na fila — fila funda não é órfão."""
    auth_client = auth_client_with_doc
    with patch(_START):
        assert await _trigger(auth_client) == 202

    run = await _latest_run(auth_client.ws_id, db)
    run.started_at = datetime.now(timezone.utc) - timedelta(minutes=30)
    run.celery_task_id = "task-na-fila"
    await db.commit()

    with patch(_START):
        assert await _trigger(auth_client) == 409

    await db.refresh(run)
    assert run.status == PipelineRunStatus.pending
    assert run.failure_reason is None
