"""Fakes in-memory de ``DocumentRepository`` + ``ClassificationService``.

Implementam os Protocols declarados em
``backend.app.application.document._protocols`` via duck typing.
``FakeClassificationService`` devolve resultado fixo configurado no
construtor — evita rodar LLM real nos testes.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional

from backend.app.models.document import Document, DocumentStatus, DocumentType


class FakeDocumentRepository:
    def __init__(self) -> None:
        self._docs: dict[str, Document] = {}

    def _ensure_defaults(self, doc: Document) -> None:
        if not doc.id:
            doc.id = str(uuid.uuid4())
        if doc.uploaded_at is None:
            doc.uploaded_at = datetime.now(timezone.utc)

    async def list(
        self,
        workspace_id: str,
        *,
        statuses: Optional[Iterable[DocumentStatus]] = None,
        doc_type: Optional[DocumentType] = None,
    ) -> list[Document]:
        status_set: Optional[set[DocumentStatus]] = None
        if statuses is not None:
            seq = list(statuses)
            if not seq:
                return []
            status_set = set(seq)

        docs: list[Document] = []
        for d in self._docs.values():
            if d.workspace_id != workspace_id:
                continue
            if status_set is not None and d.status not in status_set:
                continue
            if doc_type is not None and d.doc_type != doc_type:
                continue
            docs.append(d)
        docs.sort(key=lambda d: d.uploaded_at, reverse=True)
        return docs

    async def get_by_id(self, workspace_id: str, document_id: str) -> Optional[Document]:
        d = self._docs.get(document_id)
        if d is None or d.workspace_id != workspace_id:
            return None
        return d

    async def find_fuzzy_duplicate_id(
        self,
        workspace_id: str,
        *,
        doc_type: DocumentType,
        bank_code: str,
        period: str,
        exclude_id: Optional[str] = None,
    ) -> Optional[str]:
        for d in self._docs.values():
            if d.workspace_id != workspace_id:
                continue
            if d.id == exclude_id:
                continue
            if d.doc_type == doc_type and d.bank_code == bank_code and d.period == period:
                return d.id
        return None

    async def list_non_error(self, workspace_id: str) -> list[Document]:
        return [
            d
            for d in self._docs.values()
            if d.workspace_id == workspace_id and d.status != DocumentStatus.error
        ]

    async def add(self, document: Document, *, flush: bool = True) -> Document:
        self._ensure_defaults(document)
        self._docs[document.id] = document
        return document

    async def delete(self, document: Document) -> None:
        self._docs.pop(document.id, None)


class FakeClassificationService:
    """Devolve o dict passado no construtor — satisfaz
    ``ClassificationServiceProtocol``. Registra as chamadas em
    ``calls`` para assertions.
    """

    def __init__(self, *, result: dict[str, Any]) -> None:
        self._result = result
        self.calls: list[tuple[Path, Path]] = []

    def classify(self, file_path: Path, classification_base: Path) -> dict[str, Any]:
        self.calls.append((file_path, classification_base))
        return dict(self._result)


__all__ = [
    "FakeClassificationService",
    "FakeDocumentRepository",
]
