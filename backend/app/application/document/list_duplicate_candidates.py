"""Use case: lista documentos marcados como possível duplicata fuzzy."""

from __future__ import annotations

from backend.app.application.document._protocols import (
    DocumentRepositoryProtocol,
)
from backend.app.schemas.dto.document import (
    DocumentListResponse,
    document_to_response,
)


async def list_duplicate_candidates(
    workspace_id: str,
    *,
    repo: DocumentRepositoryProtocol,
) -> DocumentListResponse:
    """Retorna docs cujo ``possible_duplicate_of_id`` está preenchido —
    apontados pela heurística ``(doc_type, bank_code, period)`` idêntica
    mas hash diferente. UI mostra para o usuário decidir manter ou
    remover. ADR-081 (dedupe fuzzy).
    """
    docs = await repo.list_non_error(workspace_id)
    flagged = [d for d in docs if d.possible_duplicate_of_id is not None]
    return DocumentListResponse(
        documents=[document_to_response(d) for d in flagged],
        total=len(flagged),
    )
