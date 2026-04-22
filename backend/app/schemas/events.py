"""Pydantic models for WebSocket pipeline events."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class PipelineEvent(BaseModel):
    """Base event sent over WebSocket / Redis Pub/Sub."""

    event: str
    run_id: str
    timestamp: datetime
    stage: Optional[str] = None
    status: Optional[str] = None
    progress_pct: Optional[int] = None
    error: Optional[str] = None
    detail: Optional[dict[str, Any]] = None


class StageEvent(PipelineEvent):
    """Event for stage-level changes (started, completed, failed, skipped, needs_review)."""

    stage: str


class RunEvent(PipelineEvent):
    """Event for run-level changes (run_completed, run_failed, run_cancelled)."""

    pass


class ErrorEvent(PipelineEvent):
    """Event for error conditions."""

    error: str
