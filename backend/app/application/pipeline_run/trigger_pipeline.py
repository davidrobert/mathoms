"""Use case: dispara execução de pipeline (validação + insert + kickoff)."""

from __future__ import annotations

import logging

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.application.base.errors import ConflictError, ValidationError
from backend.app.core.config import settings
from backend.app.models.document import DOCUMENT_CLASSIFIED_OK, Document, DocumentStatus
from backend.app.models.goal import Goal
from backend.app.models.pipeline_artifact import PipelineArtifact
from backend.app.models.pipeline_run import PipelineRun, PipelineRunStatus
from backend.app.schemas.pipeline import PipelineRunRequest, PipelineRunResponse
from backend.app.services.pipeline_service import resolve_llm_tier_async, start_pipeline_run

_logger = logging.getLogger("mathoms.pipeline.trigger")

_ACTIVE_RUN_MESSAGE = "Já existe uma execução ativa neste workspace. Cancele ou aguarde."
_MISSING_IF_GOAL_MESSAGE = (
    "Defina sua meta de Independência Financeira antes de processar. "
    "Acesse Plano → Meta IF para configurar."
)


async def trigger_pipeline(
    workspace_id: str, body: PipelineRunRequest, *, db: AsyncSession
) -> PipelineRunResponse:
    await _check_no_active_run(workspace_id, db=db)
    await _require_if_goal(workspace_id, db=db)
    doc_count, new_doc_count = await _count_documents(workspace_id, db=db)
    _validate_counts(body, doc_count=doc_count, new_doc_count=new_doc_count)
    _validate_data_dir(workspace_id, body=body)

    incremental_doc_ids, incremental_doc_paths = await _resolve_incremental(
        workspace_id, body=body, db=db
    )
    stages = _resolve_stages(body)
    base_run_id, base_run_fallback_stages = await _resolve_base_run(
        workspace_id, from_stage=body.from_stage, stages=stages, db=db
    )

    tier = await resolve_llm_tier_async(db, workspace_id)
    run = await _create_run(
        workspace_id,
        body=body,
        doc_count=doc_count,
        incremental_doc_ids=incremental_doc_ids,
        tier=tier,
        base_run_id=base_run_id,
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
        base_run_id=base_run_id,
        base_run_fallback_stages=base_run_fallback_stages,
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


async def _require_if_goal(workspace_id: str, *, db: AsyncSession) -> None:
    """Bloqueia pipeline se não há meta IF vigente — E5 falharia com KeyError lá na frente."""
    result = await db.execute(
        select(func.count())
        .select_from(Goal)
        .where(
            Goal.workspace_id == workspace_id,
            Goal.type == "INDEPENDENCIA_FINANCEIRA",
            Goal.effective_to.is_(None),
        )
    )
    if (result.scalar() or 0) == 0:
        raise ValidationError(_MISSING_IF_GOAL_MESSAGE)


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
            "Nenhum documento novo desde a última execução. Use 'Processar todos' para reprocessar."
        )
    if doc_count == 0 and not body.from_stage:
        raise ValidationError(
            "Nenhum documento pronto para processar. Envie documentos antes de executar o pipeline."
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


def _stage_forms(artifact_stage: str) -> set[str]:
    """Formas legada + descritiva de um artifact stage (janela F9.2 → F9.6)."""
    from pipeline.stage_spec import LEGACY_TO_DESCRIPTIVE

    return {artifact_stage, LEGACY_TO_DESCRIPTIVE.get(artifact_stage, artifact_stage)}


async def _runs_with_artifacts(workspace_id: str, artifact_stage: str, *, db: AsyncSession):
    result = await db.execute(
        select(PipelineArtifact.pipeline_run_id)
        .where(
            PipelineArtifact.workspace_id == workspace_id,
            PipelineArtifact.stage.in_(_stage_forms(artifact_stage)),
        )
        .distinct()
    )
    return {row[0] for row in result}


async def _latest_run_with_all(
    workspace_id: str, needed: frozenset[str], *, db: AsyncSession
) -> str | None:
    """Run mais recente do workspace com artefatos de TODOS os stages pedidos (superset)."""
    candidates: set[str] | None = None
    for artifact_stage in sorted(needed):
        runs = await _runs_with_artifacts(workspace_id, artifact_stage, db=db)
        candidates = runs if candidates is None else candidates & runs
        if not candidates:
            return None
    result = await db.execute(
        select(PipelineRun.id)
        .where(PipelineRun.id.in_(candidates))
        .order_by(PipelineRun.started_at.desc())
        .limit(1)
    )
    return result.scalar_one()


async def _resolve_base_run(
    workspace_id: str, *, from_stage: str | None, stages: list[str], db: AsyncSession
) -> tuple[str | None, list[str]]:
    """Resolve o run base coerente para ``from_stage`` (ADR-291)."""
    # Pin em run ÚNICO — nunca latest-per-stage — preserva os invariantes
    # cross-account da ADR-241 (E3↔E4↔E5 internamente consistentes entre si).
    # Presença de rows em pipeline_artifacts é o critério (sessão por-stage só
    # comita em sucesso), não pipeline_runs.status.
    from pipeline.stage_spec import run_scoped_upstream_reads

    needed = run_scoped_upstream_reads(stages) if from_stage else frozenset()
    if not needed:
        return None, []
    base_run_id = await _latest_run_with_all(workspace_id, needed, db=db)
    if base_run_id is None:
        raise ValidationError(
            f"Reprocessar a partir de {from_stage} requer uma execução anterior "
            f"com artefatos de {', '.join(sorted(needed))}. "
            "Execute o pipeline completo primeiro."
        )
    fallback_stages = sorted({form for stage in needed for form in _stage_forms(stage)})
    _log_base_run_resolved(workspace_id, from_stage, base_run_id, fallback_stages)
    return base_run_id, fallback_stages


def _log_base_run_resolved(
    workspace_id: str, from_stage: str | None, base_run_id: str, fallback_stages: list[str]
) -> None:
    _logger.info(
        "mathoms.pipeline.trigger.base_run_resolved",
        extra={
            "workspace_id": workspace_id,
            "from_stage": from_stage,
            "base_run_id": base_run_id,
            "fallback_stages": fallback_stages,
        },
    )


async def _create_run(
    workspace_id: str,
    *,
    body: PipelineRunRequest,
    doc_count: int,
    incremental_doc_ids: list[str] | None,
    tier: str,
    base_run_id: str | None = None,
    db: AsyncSession,
) -> PipelineRun:
    run = PipelineRun(
        workspace_id=workspace_id,
        status=PipelineRunStatus.pending,
        total_documents=doc_count,
        incremental=body.incremental,
        incremental_doc_ids=incremental_doc_ids,
        tier_at_run=tier,
        base_run_id=base_run_id,
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
