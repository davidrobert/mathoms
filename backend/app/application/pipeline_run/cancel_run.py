"""Use case: cancela um run ativo — inclusive um pausado para review (ADR-417 D1)."""

from __future__ import annotations

from fastapi import Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.base.errors import ConflictError
from backend.app.application.pipeline_run._common import fetch_run
from backend.app.models.pipeline_run import PipelineRun, PipelineRunStatus
from backend.app.models.stage_review import StageReview, StageReviewStatus
from backend.app.schemas.pipeline import RunActionResponse
from backend.app.services.audit import AuditAction, audit_log
from backend.app.services.pipeline.dispatch_contract import CANCELLABLE_STATUSES
from backend.app.services.pipeline.pipeline_service import cancel_pipeline_run

_DETAIL_DISCARDED = "Processamento descartado. As conferências pendentes deixam de ser necessárias."
_DETAIL_INTERRUPTED = "Cancelamento solicitado. Pipeline parará após a etapa atual."
# A40.l87 — o retorno de `cancel_pipeline_run` era DESCARTADO: quando o flip é no-op (o
# run virou terminal entre o SELECT e o UPDATE do service), respondíamos sucesso sobre
# nada feito. Mesma classe de compensação silenciosa que a ADR-359 loga como
# `compensation_noop`.
_RACE = "A execução mudou de estado durante o cancelamento. Recarregue a página."


async def _pending_reviews(run_id: str, *, db: AsyncSession) -> int:
    result = await db.execute(
        select(func.count())
        .select_from(StageReview)
        .where(
            StageReview.pipeline_run_id == run_id,
            StageReview.status == StageReviewStatus.pending,
        )
    )
    return result.scalar() or 0


async def _abandon_context(run: PipelineRun, *, db: AsyncSession) -> dict:
    """Snapshot do que se perdeu no momento do ato — é para isso que serve o audit."""
    return {
        "previous_status": str(getattr(run.status, "value", run.status)),
        "paused_at_stage": run.paused_at_stage,
        "pending_reviews": await _pending_reviews(run.id, db=db),
    }


def _reject_if_not_cancellable(run: PipelineRun) -> None:
    """A guarda é DUPLICADA (aqui e em `cancel_pipeline_run`): alargar só o service
    deixaria o endpoint respondendo 409 com o teste de service verde — verde-falso no
    critério de aceite da A40.l27. As duas leem a MESMA constante por isso."""
    if run.status not in CANCELLABLE_STATUSES:
        raise ConflictError(f"Execução não pode ser cancelada (status: {run.status})")


async def _registrar_abandono(
    run_id: str,
    workspace_id: str,
    details: dict,
    *,
    db: AsyncSession,
    actor_user_id: str | None,
    request: Request | None,
) -> None:
    await audit_log(
        db,
        action=AuditAction.pipeline_run_cancel,
        resource_type="pipeline_run",
        resource_id=run_id,
        workspace_id=workspace_id,
        actor_user_id=actor_user_id,
        request=request,
        details=details,
    )
    await db.commit()


async def cancel_run(
    workspace_id: str,
    run_id: str,
    *,
    db: AsyncSession,
    actor_user_id: str | None = None,
    request: Request | None = None,
) -> RunActionResponse:
    run = await fetch_run(workspace_id, run_id, db=db)
    _reject_if_not_cancellable(run)
    discarding = run.status == PipelineRunStatus.needs_review
    details = await _abandon_context(run, db=db)
    if not cancel_pipeline_run(run_id):
        raise ConflictError(_RACE)
    await _registrar_abandono(
        run_id, workspace_id, details, db=db, actor_user_id=actor_user_id, request=request
    )
    detail = _DETAIL_DISCARDED if discarding else _DETAIL_INTERRUPTED
    return RunActionResponse(detail=detail, run_id=run_id)
