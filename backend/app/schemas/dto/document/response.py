"""Response DTOs do agregado ``Document``.

Wire shape retornado pela API — mudanças aqui são **breaking** para o
frontend (``lib/api.ts`` / tela de documentos). Compat binária com
``schemas.document.DocumentResponse`` é preservada durante A6e via
legacy shim.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel

from backend.app.models.document import DocumentStatus, DocumentType


class DocumentResponse(BaseModel):
    """Documento enviado ao workspace, com metadata de classificação."""

    id: str
    workspace_id: str
    original_name: str
    stored_path: Optional[str] = None
    doc_type: Optional[DocumentType] = None
    e0_doc_type: Optional[str] = None
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
    """Wrapper paginação-ready para ``GET /documents``."""

    documents: list[DocumentResponse]
    total: int


class DocumentUploadResponse(BaseModel):
    """Resposta do ``POST /documents/upload`` (multi-file).

    ``skipped_duplicates`` é a lista de nomes de arquivo que caíram na
    unique index de ``content_hash`` — não geraram row nova, mas o caller
    quer saber para dar feedback na UI.
    """

    documents: list[DocumentResponse]
    skipped_duplicates: list[str] = []
    total_uploaded: int = 0
    total_skipped: int = 0


class DocumentExtractJsonResponse(BaseModel):
    """Resposta do endpoint de debug ``GET /documents/{id}/extract-json``."""

    filename: str
    data: Any
    all_candidates: list[str]


class DocumentReclassifyResponse(BaseModel):
    """Resposta do ``POST /documents/reclassify`` (batch reclassify)."""

    total: int
    updated: int
    skipped: int
    errors: int
