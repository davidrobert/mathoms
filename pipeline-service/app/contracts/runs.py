"""DTOs for run-level endpoints."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from .stages import StageExecuteResponse


class RunStartRequest(BaseModel):
    """Input to POST /api/v1/pipeline/runs — run a sequence of stages."""

    run_id: str
    workspace_id: str
    workspace_root: str
    config_dir: Optional[str] = None
    stages: list[str] = Field(..., min_length=1)
    skip_llm: bool = True
    stop_on_error: bool = True
    incremental: bool = False
    incremental_doc_paths: list[str] = Field(default_factory=list)
    base_run_id: Optional[str] = Field(
        default=None,
        description="Run base para fallback run-pinado em from_stage (ADR-291/ADR-303)",
    )
    base_run_fallback_stages: list[str] = Field(
        default_factory=list,
        description="Stages upstream lidos do run base (ADR-291/ADR-303)",
    )


class RunSummaryResponse(BaseModel):
    """Aggregated result of a multi-stage run."""

    run_id: str
    workspace_id: str
    success: bool
    started_at: str
    finished_at: str
    stages: list[StageExecuteResponse]
    failed_stage: Optional[str] = None


class ServiceHealthResponse(BaseModel):
    status: str = "ok"
    service: str = "pipeline-service"
    version: str
