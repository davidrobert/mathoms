"""Pydantic schemas for Pipeline execution endpoints."""

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, field_serializer, field_validator

from backend.app.models.pipeline_run import PipelineRunStatus, PipelineStageStatus
from backend.app.models.stage_review import StageReviewStatus

VALID_FROM_STAGES = {"E0", "E1", "E2", "E3", "E4", "E5", "E5.N", "E6", "E7"}


class PipelineRunRequest(BaseModel):
    from_stage: Optional[str] = None
    skip_llm: bool = True
    stop_on_error: bool = True
    incremental: bool = False

    @field_validator("from_stage")
    @classmethod
    def validate_from_stage(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in VALID_FROM_STAGES:
            raise ValueError(f"from_stage inválido: {v}. Válidos: {sorted(VALID_FROM_STAGES)}")
        return v


class PipelineStageLogResponse(BaseModel):
    id: str
    stage: str
    status: PipelineStageStatus
    output_summary: Optional[dict] = None
    errors: Optional[str] = None
    duration_ms: Optional[int] = None
    started_at: datetime
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}

    @field_serializer("started_at", "completed_at")
    @classmethod
    def _serialize_dt_utc(cls, v: datetime | None) -> str | None:
        if v is None:
            return None
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        return v.isoformat()


class StageReviewResponse(BaseModel):
    id: str
    pipeline_run_id: str
    stage: str
    status: StageReviewStatus
    original_output_json: Optional[dict] = None
    edited_output_json: Optional[dict] = None
    validation_errors: Optional[str] = None
    reviewer_notes: Optional[str] = None
    created_at: datetime
    reviewed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class StageReviewActionRequest(BaseModel):
    action: str  # "approve" or "edit"
    edited_output_json: Optional[dict] = None
    reviewer_notes: Optional[str] = None

    @field_validator("action")
    @classmethod
    def validate_action(cls, v: str) -> str:
        if v not in ("approve", "edit"):
            raise ValueError("action must be 'approve' or 'edit'")
        return v


class PipelineRunResponse(BaseModel):
    id: str
    workspace_id: str
    status: PipelineRunStatus
    current_stage: Optional[str] = None
    failed_at_stage: Optional[str] = None
    paused_at_stage: Optional[str] = None
    tier_at_run: str = "free"
    total_documents: Optional[int] = None
    incremental: bool = False
    celery_task_id: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    stage_logs: list[PipelineStageLogResponse] = []
    report_id: Optional[str] = None

    model_config = {"from_attributes": True}

    @field_serializer("started_at", "completed_at")
    @classmethod
    def _serialize_dt_utc(cls, v: datetime | None) -> str | None:
        if v is None:
            return None
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        return v.isoformat()


class PipelineRunListResponse(BaseModel):
    runs: list[PipelineRunResponse]
    total: int
