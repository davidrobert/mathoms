"""Use case: dispara execução de pipeline (validação + insert + kickoff)."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.application.base.errors import ConflictError, ValidationError
from backend.app.core.config import settings
from backend.app.models.document import DOCUMENT_CLASSIFIED_OK, Document, DocumentStatus
from backend.app.models.pipeline_run import PipelineRun, PipelineRunStatus
from backend.app.schemas.pipeline import PipelineRunRequest, PipelineRunResponse
from backend.app.services.pipeline_service import resolve_llm_tier_async, start_pipeline_run

_ACTIVE_RUN_MESSAGE = "Já existe uma execução ativa neste workspace. Cancele ou aguarde."


async def trigger_pipeline(
    workspace_id: str, body: PipelineRunRequest, *, db: AsyncSession
) -> PipelineRunResponse:
    await _check_no_active_run(workspace_id, db=db)
    doc_count, new_doc_count = await _count_documents(workspace_id, db=db)
    _validate_counts(body, doc_count=doc_count, new_doc_count=new_doc_count)
    _validate_data_dir(workspace_id, body=body)

    incremental_doc_ids, incremental_doc_paths = await _resolve_incremental(
        workspace_id, body=body, db=db
    )
    stages = _resolve_stages(body)

    tier = await resolve_llm_tier_async(db, workspace_id)
    run = await _create_run(
        workspace_id,
        body=body,
        doc_count=doc_count,
        incremental_doc_ids=incremental_doc_ids,
        tier=tier,
        db=db,
    )

    start_pipeline_run(
        run_id=run.id,
        ws_id=workspace_id,
        stages=stages,
        skip_llm=body.skip_llm,
        stop_on_error=body.stop_on_error,
        tier=tier,
        incremental=body.incremental,
        incremental_doc_paths=incremental_doc_paths or [],
    )
    return PipelineRunResponse.model_validate(run)


async def _check_no_active_run(workspace_id: str, *, db: AsyncSession) -> None:
    """UX-level fast-path. O guard authoritativo é o partial unique index
    ``ux_pipeline_runs_ws_active`` (migração i4c5d6e7f8a9)."""
    result = await db.execute(
        select(func.count())
        .select_from(PipelineRun)
        .where(
            PipelineRun.workspace_id == workspace_id,
            PipelineRun.status.in_([PipelineRunStatus.pending, PipelineRunStatus.running]),
        )
    )
    if (result.scalar() or 0) > 0:
        raise ConflictError(_ACTIVE_RUN_MESSAGE)


async def _count_documents(workspace_id: str, *, db: AsyncSession) -> tuple[int, int]:
    doc_count_result = await db.execute(
        select(func.count())
        .select_from(Document)
        .where(
            Document.workspace_id == workspace_id,
            Document.status.in_(DOCUMENT_CLASSIFIED_OK),
        )
    )
    doc_count = doc_count_result.scalar() or 0

    new_doc_count_result = await db.execute(
        select(func.count())
        .select_from(Document)
        .where(
            Document.workspace_id == workspace_id,
            Document.status == DocumentStatus.ready,
            Document.pipeline_last_run_at.is_(None),
        )
    )
    new_doc_count = new_doc_count_result.scalar() or 0
    return doc_count, new_doc_count


def _validate_counts(body: PipelineRunRequest, *, doc_count: int, new_doc_count: int) -> None:
    if body.incremental and new_doc_count == 0:
        raise ValidationError(
            "Nenhum documento novo desde a última execução. "
            "Use 'Processar todos' para reprocessar."
        )
    if doc_count == 0 and not body.from_stage:
        raise ValidationError(
            "Nenhum documento pronto para processar. "
            "Envie documentos antes de executar o pipeline."
        )


def _validate_data_dir(workspace_id: str, *, body: PipelineRunRequest) -> None:
    if body.from_stage:
        return
    tenant_data = settings.STORAGE_ROOT / workspace_id / "data"
    has_files = tenant_data.exists() and any(
        sub.is_dir() and any(sub.iterdir()) for sub in tenant_data.iterdir()
    )
    if not has_files:
        raise ValidationError(
            "Nenhum documento financeiro encontrado no workspace. "
            "Os documentos podem não ter sido classificados corretamente."
        )


async def _resolve_incremental(
    workspace_id: str, *, body: PipelineRunRequest, db: AsyncSession
) -> tuple[list[str] | None, list[str] | None]:
    if not body.incremental:
        return None, None
    result = await db.execute(
        select(Document.id, Document.stored_path).where(
            Document.workspace_id == workspace_id,
            Document.status == DocumentStatus.ready,
            Document.pipeline_last_run_at.is_(None),
        )
    )
    rows = result.all()
    doc_ids = [str(r.id) for r in rows]
    doc_paths = [r.stored_path for r in rows if r.stored_path]
    if not doc_paths:
        raise ValidationError(
            "Modo incremental requer documentos novos com caminho de armazenamento válido. "
            "Corrija documentos sem arquivo associado ou use 'Processar todos'."
        )
    return doc_ids, doc_paths


def _resolve_stages(body: PipelineRunRequest) -> list[str]:
    from pipeline.orchestrator import DETERMINISTIC_ORDER, FROM_MAP, FULL_ORDER

    if body.from_stage:
        stages = FROM_MAP.get(body.from_stage)
        if stages is None:
            raise ValidationError(f"from_stage inválido: {body.from_stage}")
        return stages
    if body.skip_llm:
        return DETERMINISTIC_ORDER[:]
    return FULL_ORDER[:]


async def _create_run(
    workspace_id: str,
    *,
    body: PipelineRunRequest,
    doc_count: int,
    incremental_doc_ids: list[str] | None,
    tier: str,
    db: AsyncSession,
) -> PipelineRun:
    run = PipelineRun(
        workspace_id=workspace_id,
        status=PipelineRunStatus.pending,
        total_documents=doc_count,
        incremental=body.incremental,
        incremental_doc_ids=incremental_doc_ids,
        tier_at_run=tier,
    )
    db.add(run)
    try:
        await db.commit()
    except IntegrityError as exc:
        # `ux_pipeline_runs_ws_active` colidiu — race resolvida no DB.
        await db.rollback()
        raise ConflictError(_ACTIVE_RUN_MESSAGE) from exc

    result = await db.execute(
        select(PipelineRun)
        .where(PipelineRun.workspace_id == workspace_id, PipelineRun.id == run.id)
        .options(selectinload(PipelineRun.stage_logs))
    )
    return result.scalar_one()
