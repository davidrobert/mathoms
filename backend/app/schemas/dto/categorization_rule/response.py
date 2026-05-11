"""Response DTOs de ``CategorizationRule`` — saída de GET rules (ADR-186 §D3 · A12 P3)."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class CategorizationRuleResponse(BaseModel):
    """Regra promovida — o que a UI consome."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    workspace_id: str
    keyword: str
    target_category: str
    priority: int
    enabled: bool
    origin_override_id: Optional[str] = None
    created_by_user_id: Optional[str] = None
    applied_count: int
    # ADR-188 §D3 — split de ``revert_count`` em 2 sinais distintos.
    revert_count_manual_edit: int
    revert_count_rule_disabled: int
    created_at: datetime
    updated_at: datetime
