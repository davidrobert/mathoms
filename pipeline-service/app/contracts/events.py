"""DTOs for stage/run events (Redis pub/sub + WebSocket)."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class StageEvent(BaseModel):
    """Wire format for events on channel `pipeline:{run_id}`.

    Mirrors the shape produced by `backend.app.services.events` so both
    backend (legacy pub/sub) and pipeline-service (HTTP pub/sub) emit the
    same envelope. WebSocket subscribers see the union of both streams.
    """

    event: str
    run_id: str
    timestamp: str
    stage: Optional[str] = None
    status: Optional[str] = None
    progress_pct: Optional[int] = None
    error: Optional[str] = None
    detail: Optional[dict[str, Any]] = Field(default=None)
