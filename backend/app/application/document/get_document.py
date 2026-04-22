"""Use case: retorna um Document ou levanta ``NotFoundError``."""

from __future__ import annotations

from backend.app.application.base.errors import NotFoundError
from backend.app.application.document._protocols import (
    DocumentRepositoryProtocol,
)
from backend.app.models.document import Document


async def get_document(
    workspace_id: str,
    document_id: str,
    *,
    repo: DocumentRepositoryProtocol,
) -> Document:
    """Retorna a entidade (não o DTO) porque callers downstream
    (``get_document_file``, ``get_document_extract_json``) precisam de
    atributos como ``stored_path`` / ``bank_code`` que não trafegam no
    DTO de resposta. Use cases que retornam DTO existem à parte
    (ex.: ``update_document_classification`` devolve ``DocumentResponse``).
    """
    doc = await repo.get_by_id(workspace_id, document_id)
    if doc is None:
        raise NotFoundError(
            "Documento não encontrado", code="document_not_found"
        )
    return doc
