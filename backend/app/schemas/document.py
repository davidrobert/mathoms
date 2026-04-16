"""Pydantic schemas for Document endpoints."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from backend.app.models.document import DocumentStatus, DocumentType


class DocumentResponse(BaseModel):
    id: str
    workspace_id: str
    original_name: str
    stored_path: Optional[str] = None
    doc_type: Optional[DocumentType] = None
    bank_code: Optional[str] = None
    period: Optional[str] = None
    status: DocumentStatus
    classification_meta: Optional[dict] = None
    classification_confidence: Optional[float] = None
    needs_review: bool = False
    possible_duplicate_of_id: Optional[str] = None
    file_size_bytes: Optional[int] = None
    content_type: Optional[str] = None
    error_message: Optional[str] = None
    uploaded_at: datetime
    pipeline_last_run_at: Optional[datetime] = None
    pipeline_e2_extract_ok: Optional[bool] = None

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    documents: list[DocumentResponse]
    total: int


class DocumentUploadResponse(BaseModel):
    documents: list[DocumentResponse]
    skipped_duplicates: list[str] = []
    total_uploaded: int = 0
    total_skipped: int = 0
