"""Pydantic schemas for Document endpoints."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator

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
    pipeline_extract_notes: Optional[str] = None

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    documents: list[DocumentResponse]
    total: int


class DocumentUploadResponse(BaseModel):
    documents: list[DocumentResponse]
    skipped_duplicates: list[str] = []
    total_uploaded: int = 0
    total_skipped: int = 0


class DocumentUpdateRequest(BaseModel):
    """Correção manual de classificação pelo usuário.

    Todos os campos são opcionais — atualiza apenas os enviados (PATCH).
    Envie `null` explícito para limpar um campo.
    """

    doc_type: Optional[DocumentType] = Field(default=None)
    bank_code: Optional[str] = Field(default=None, max_length=50)
    period: Optional[str] = Field(default=None, max_length=50)

    @field_validator("bank_code", "period", mode="before")
    @classmethod
    def _empty_str_to_none(cls, v):
        if isinstance(v, str) and v.strip() == "":
            return None
        return v
