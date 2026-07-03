"""Stage-level execution endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.contracts.stages import StageExecuteRequest, StageExecuteResponse
from app.services.artifact_session import ArtifactStoreUnavailable
from app.services.stage_executor import run_stage_by_name

router = APIRouter(prefix="/api/v1/pipeline/stages", tags=["stages"])


_ERROR_RESPONSES = {
    404: {"description": "Stage desconhecido (aceita legacy ou descritivo, ADR-093)."},
    503: {"description": "DBArtifactStore/hidratação indisponível (ADR-303 D4)."},
}


@router.post("/{stage}/execute", response_model=StageExecuteResponse, responses=_ERROR_RESPONSES)
def execute_stage(stage: str, req: StageExecuteRequest) -> StageExecuteResponse:
    """Execute a single pipeline stage and return the result.

    Boundary externo: aceita nome legacy ("E3") ou descritivo (ADR-093);
    executa e responde sempre com o descritivo canônico.
    """
    from pipeline.stage_spec import STAGE_REGISTRY, resolve_stage_name

    resolved = resolve_stage_name(stage)
    if resolved not in STAGE_REGISTRY:
        raise HTTPException(
            status_code=404,
            detail=f"unknown stage '{stage}' (valid: {sorted(STAGE_REGISTRY)})",
        )
    try:
        return run_stage_by_name(resolved, req)
    except ArtifactStoreUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
