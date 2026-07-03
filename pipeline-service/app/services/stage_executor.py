"""Stage executor — thin wrapper around `pipeline.orchestrator._run_stage`.

No duplication of stage logic. The orchestrator is imported as a library
(pipeline-service lives outside the `pipeline/` package, so the framework
import ban in `dev/check_pipeline_boundaries.py` does not apply).

Hidratação de contexto (paridade com o Celery — ADR-303 §Escopo deferido,
fechado): `run_context_factory` injeta DBConfigStore + overrides + resolvers
(ADR-215/219/222) + budget hooks (ADR-173) + tarefas.md por request de stage.
Duas sessões coexistem por stage (config read-only + artifact read-write,
invariante ADR-256); fechamento ordenado: artifact primeiro, config depois.
"""

from __future__ import annotations

from pathlib import Path

from app.contracts.stages import StageExecuteRequest, StageExecuteResponse
from app.services.artifact_session import (
    ArtifactStoreUnavailable,
    commit_and_close,
    open_artifact_store,
    rollback_and_close,
)


def run_stage_by_name(stage: str, req: StageExecuteRequest) -> StageExecuteResponse:
    """Execute a single pipeline stage with a fresh hydrated WorkspaceContext.

    ADR-303 D1: sessão + ``DBArtifactStore`` por stage, injetados no ctx
    antes de ``_run_stage`` — sem isso, qualquer stage que toque artefato
    morre em ``get_artifact_store()`` (ADR-212 PR3b).
    """
    from pipeline.orchestrator import _run_stage

    hydrated = _build_hydrated_context(req)
    try:
        session, store = open_artifact_store(
            workspace_id=req.workspace_id,
            run_id=req.run_id,
            base_run_id=req.base_run_id,
            base_run_fallback_stages=req.base_run_fallback_stages,
        )
        try:
            hydrated.ctx.artifact_store = store
            result = _run_stage(hydrated.ctx, stage)
        except BaseException:
            rollback_and_close(session)
            raise
        else:
            commit_and_close(session)
    finally:
        hydrated.close()
    return StageExecuteResponse(
        stage=result.stage,
        success=result.success,
        duration_ms=result.duration_ms,
        detail=result.detail,
        error=result.error,
    )


def _build_hydrated_context(req: StageExecuteRequest):
    return build_hydrated_request_context(req)


def _import_build_hydrated():
    try:
        from backend.app.services.run_context_factory import build_hydrated_context
    except ImportError as exc:
        raise ArtifactStoreUnavailable(
            "pipeline-service requer o pacote 'backend' importável para hidratar "
            f"o contexto (run_context_factory, ADR-303 D4): {exc}"
        ) from exc
    return build_hydrated_context


def build_hydrated_request_context(req):
    """WorkspaceContext hidratado para um request HTTP (D4: falha nomeada).

    Aceita ``StageExecuteRequest`` ou ``RunStartRequest`` (mesmos campos);
    ``config_dir`` explícito vence, omitido → ``<workspace_root>/config``.
    """
    build_hydrated_context = _import_build_hydrated()
    try:
        return build_hydrated_context(
            ws_id=req.workspace_id,
            tenant_root=Path(req.workspace_root),
            run_id=req.run_id,
            config_dir=Path(req.config_dir) if req.config_dir else None,
            incremental=req.incremental,
            incremental_doc_paths=list(req.incremental_doc_paths),
            materialize_tarefas=True,
        )
    except Exception as exc:
        raise ArtifactStoreUnavailable(
            f"falha ao hidratar o WorkspaceContext (ADR-303 D4): {exc}"
        ) from exc
