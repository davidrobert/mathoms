"""Use case: remove a row de Document (arquivo em disco fica no composite)."""

from __future__ import annotations

from backend.app.application.base.errors import NotFoundError
from backend.app.application.document._protocols import (
    DocumentRepositoryProtocol,
)
from backend.app.models.document import Document


async def delete_document(
    workspace_id: str,
    document_id: str,
    *,
    repo: DocumentRepositoryProtocol,
) -> Document:
    """Remove apenas a row. Retorna a entidade para o caller (router)
    resolver ``stored_path`` → arquivo absoluto e remover do disco via
    ``StorageService`` (side-effect de filesystem fica fora do use case).
    """
    doc = await repo.get_by_id(workspace_id, document_id)
    if doc is None:
        raise NotFoundError(
            "Documento não encontrado", code="document_not_found"
        )
    await repo.delete(doc)
    return doc
