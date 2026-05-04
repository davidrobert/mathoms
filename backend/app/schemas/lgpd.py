"""LGPD self-service request/response schemas (Art. 18)."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class DataExportCreatedResponse(BaseModel):
    request_id: str
    status: str
    eta_minutes: int


class DataExportStatusResponse(BaseModel):
    request_id: str
    status: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    file_size_bytes: Optional[int] = None
    error_message: Optional[str] = None
    download_url: Optional[str] = None


class DeletionRequestResponse(BaseModel):
    user_id: str
    deletion_requested_at: datetime
    hard_delete_after: datetime
    message: str


class DeletionCanceledResponse(BaseModel):
    user_id: str
    message: str
