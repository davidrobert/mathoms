"""DTOs for stage execution endpoints."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class StageExecuteRequest(BaseModel):
    """Input to POST /api/v1/pipeline/stages/{stage}/execute.

    Backend owns the workspace root on disk and passes it by path — the
    pipeline-service runs the stage in-process using `pipeline.orchestrator`.
    Artifacts are written to/read from that root by the stage runners.
    """

    run_id: str = Field(..., description="Backend-issued PipelineRun UUID")
    workspace_id: str
    workspace_root: str = Field(..., description="Absolute path to tenant root")
    config_dir: Optional[str] = None
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


class StageExecuteResponse(BaseModel):
    """Result of a single stage execution."""

    stage: str
    success: bool
    duration_ms: float = 0.0
    detail: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    attempts: int = 1
