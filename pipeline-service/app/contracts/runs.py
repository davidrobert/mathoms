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
