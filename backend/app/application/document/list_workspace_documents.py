"""Use case: lista documentos do workspace com filtros opcionais."""

from __future__ import annotations

from typing import Optional

from backend.app.application.base.errors import ValidationError
from backend.app.application.document._protocols import (
    DocumentRepositoryProtocol,
)
from backend.app.models.document import DocumentStatus, DocumentType
from backend.app.schemas.dto.document import (
    DocumentListResponse,
    document_to_response,
)


async def list_workspace_documents(
    workspace_id: str,
    *,
    repo: DocumentRepositoryProtocol,
    status_filter: Optional[str] = None,
    doc_type_filter: Optional[str] = None,
) -> DocumentListResponse:
    """``status_filter`` aceita CSV (``"ready,processed"``). Campos
    inválidos levantam ``ValidationError`` — router traduz para 400.
    """
    statuses = _parse_statuses(status_filter)
    doc_type = _parse_doc_type(doc_type_filter)

    docs = await repo.list(workspace_id, statuses=statuses, doc_type=doc_type)
    return DocumentListResponse(
        documents=[document_to_response(d) for d in docs],
        total=len(docs),
    )


def _parse_statuses(raw: Optional[str]) -> Optional[list[DocumentStatus]]:
    if not raw:
        return None
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    allowed = {m.value for m in DocumentStatus}
    for p in parts:
        if p not in allowed:
            raise ValidationError(
                f"Status inválido: {p}", code="invalid_status"
            )
    return [DocumentStatus(p) for p in parts]


def _parse_doc_type(raw: Optional[str]) -> Optional[DocumentType]:
    if not raw:
        return None
    try:
        return DocumentType(raw)
    except ValueError as exc:
        raise ValidationError(
            f"Tipo inválido: {raw}", code="invalid_doc_type"
        ) from exc
