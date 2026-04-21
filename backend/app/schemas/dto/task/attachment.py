"""DTOs do sub-agregado ``TaskAttachment`` (ADR-074).

Só metadata — o binário é servido por ``GET /download`` que devolve
``FileResponse`` direto do storage.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class TaskAttachmentResponse(BaseModel):
    """Metadados de um anexo de task."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    task_id: str
    workspace_id: str
    original_filename: str
    content_type: Optional[str] = None
    size_bytes: Optional[int] = None
    uploaded_by: Optional[str] = None
    created_at: datetime


class TaskAttachmentListResponse(BaseModel):
    """Wrapper paginação-ready para ``GET /tasks/{id}/attachments``."""

    attachments: list[TaskAttachmentResponse]
    total: int
