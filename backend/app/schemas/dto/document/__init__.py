"""DTOs do agregado ``Document``.

Re-exports convenientes — prefira estes imports ao invés de alcançar
módulos internos, para manter o pacote como fronteira do agregado.
"""

from backend.app.schemas.dto.document.command import (
    DocumentUpdateCommand,
)
from backend.app.schemas.dto.document.mapper import (
    document_to_response,
)
from backend.app.schemas.dto.document.response import (
    DocumentExtractJsonResponse,
    DocumentListResponse,
    DocumentReclassifyResponse,
    DocumentResponse,
    DocumentUploadResponse,
)

__all__ = [
    "DocumentExtractJsonResponse",
    "DocumentListResponse",
    "DocumentReclassifyResponse",
    "DocumentResponse",
    "DocumentUpdateCommand",
    "DocumentUploadResponse",
    "document_to_response",
]
