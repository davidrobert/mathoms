"""Report request/response schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ReportResponse(BaseModel):
    id: str
    workspace_id: str
    title: str
    period: Optional[str] = None
    size_bytes: Optional[int] = None
    score: Optional[float] = None
    patrimonio_liquido: Optional[float] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ReportListResponse(BaseModel):
    reports: list[ReportResponse]
    total: int
