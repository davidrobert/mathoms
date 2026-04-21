"""Legacy shim para ``schemas.document``.

Os DTOs canônicos do agregado ``Document`` vivem em
``backend/app/schemas/dto/document/`` (A6e.5 — ADR-101). Este módulo
re-exporta com os nomes antigos para que:

- testes legados (``from backend.app.schemas.document import DocumentResponse``)
  continuem passando sem modificação;
- integrações externas que possam ter importado esses símbolos não
  quebrem durante a janela de migração.

Preferir nas chamadas novas::

    from backend.app.schemas.dto.document import (
        DocumentResponse, DocumentListResponse, DocumentUploadResponse,
        DocumentUpdateCommand,
    )
"""

from __future__ import annotations

from backend.app.schemas.dto.document.command import (
    DocumentUpdateCommand as DocumentUpdateRequest,
)
from backend.app.schemas.dto.document.response import (
    DocumentListResponse,
    DocumentResponse,
    DocumentUploadResponse,
)

__all__ = [
    "DocumentListResponse",
    "DocumentResponse",
    "DocumentUpdateRequest",
    "DocumentUploadResponse",
]
