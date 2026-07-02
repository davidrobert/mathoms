"""Run-level execution endpoints — sequence a full stage pipeline."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.contracts.runs import RunStartRequest, RunSummaryResponse
from app.services.artifact_session import ArtifactStoreUnavailable
from app.services.run_coordinator import run_sequence

router = APIRouter(prefix="/api/v1/pipeline/runs", tags=["runs"])


@router.post("", response_model=RunSummaryResponse)
def start_run(req: RunStartRequest) -> RunSummaryResponse:
    """Execute the requested stage sequence synchronously.

    Backend caller is responsible for run_id generation and DB persistence;
    this service is stateless and returns the aggregated result only.
    Boundary externo: aceita nomes legacy ou descritivos (ADR-093).
    """
    from pipeline.stage_spec import STAGE_REGISTRY, resolve_stage_name

    resolved = [resolve_stage_name(s) for s in req.stages]
    unknown = [orig for orig, r in zip(req.stages, resolved) if r not in STAGE_REGISTRY]
    if unknown:
        raise HTTPException(
            status_code=400,
            detail=f"unknown stage(s): {unknown}",
        )
    try:
        return run_sequence(req.model_copy(update={"stages": resolved}))
    except ArtifactStoreUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
