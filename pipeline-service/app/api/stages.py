"""Stage-level execution endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.contracts.stages import StageExecuteRequest, StageExecuteResponse
from app.services.stage_executor import run_stage_by_name

router = APIRouter(prefix="/api/v1/pipeline/stages", tags=["stages"])


@router.post("/{stage}/execute", response_model=StageExecuteResponse)
def execute_stage(stage: str, req: StageExecuteRequest) -> StageExecuteResponse:
    """Execute a single pipeline stage and return the result."""
    from pipeline.stage_spec import STAGE_REGISTRY

    if stage not in STAGE_REGISTRY:
        raise HTTPException(
            status_code=404,
            detail=f"unknown stage '{stage}' (valid: {sorted(STAGE_REGISTRY)})",
        )
    return run_stage_by_name(stage, req)
