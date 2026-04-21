"""Run-level execution endpoints — sequence a full stage pipeline."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.contracts.runs import RunStartRequest, RunSummaryResponse
from app.services.run_coordinator import run_sequence

router = APIRouter(prefix="/api/v1/pipeline/runs", tags=["runs"])


@router.post("", response_model=RunSummaryResponse)
def start_run(req: RunStartRequest) -> RunSummaryResponse:
    """Execute the requested stage sequence synchronously.

    Backend caller is responsible for run_id generation and DB persistence;
    this service is stateless and returns the aggregated result only.
    """
    from pipeline.stage_spec import STAGE_REGISTRY

    unknown = [s for s in req.stages if s not in STAGE_REGISTRY]
    if unknown:
        raise HTTPException(
            status_code=400,
            detail=f"unknown stage(s): {unknown}",
        )
    return run_sequence(req)
