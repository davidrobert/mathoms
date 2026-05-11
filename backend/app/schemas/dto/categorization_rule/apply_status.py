"""Status DTOs do apply retroativo async (ADR-188 PR3)."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel


class RuleApplyStatusResponse(BaseModel):
    """``GET /rules/{rule_id}/apply-status`` — espelha hash Redis ``apply_status``."""

    rule_id: str
    workspace_id: str
    status: Literal["pending", "completed", "failed", "unknown"]
    job_id: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    applied_count: int = 0
    failed_count: int = 0
    error: Optional[str] = None


class AsyncRuleCreatedResponse(BaseModel):
    """202 do ``POST /rules`` quando matches >``SYNC_APPLY_THRESHOLD`` — mensagem amigável (financial-planner)."""

    rule_id: str
    workspace_id: str
    status: Literal["pending"] = "pending"
    job_id: str
    message: str
