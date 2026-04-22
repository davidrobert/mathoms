"""Protocols consumidos pelos use cases do agregado ``Document``.

Além do repo, expõe ``ClassificationServiceProtocol`` para isolar o
side-effect de extração + LLM fallback (ver
``backend.app.services.document_classification.classify_document`` —
mantido intacto; use case chama, nunca reimplementa). Fakes substituem
em teste para evitar rodar LLM/filesystem.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Optional, Protocol

from backend.app.models.document import Document, DocumentStatus, DocumentType


class DocumentRepositoryProtocol(Protocol):
    async def list(
        self,
        workspace_id: str,
        *,
        statuses: Optional[Iterable[DocumentStatus]] = None,
        doc_type: Optional[DocumentType] = None,
    ) -> list[Document]: ...

    async def get_by_id(
        self, workspace_id: str, document_id: str
    ) -> Optional[Document]: ...

    async def find_fuzzy_duplicate_id(
        self,
        workspace_id: str,
        *,
        doc_type: DocumentType,
        bank_code: str,
        period: str,
        exclude_id: Optional[str] = None,
    ) -> Optional[str]: ...

    async def list_non_error(self, workspace_id: str) -> list[Document]: ...

    async def delete(self, document: Document) -> None: ...


class ClassificationServiceProtocol(Protocol):
    """Wrapper fino de ``document_classification.classify_document``.

    Recebe path do arquivo + base de config; retorna dict com shape
    documentado em ADR-081. Fake pode devolver valor fixo.
    """

    def classify(
        self, file_path: Path, classification_base: Path
    ) -> dict[str, Any]: ...
