"""Use case: reclassifica 1 documento (usado pelo bulk reclassify router)."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from backend.app.application.base.errors import NotFoundError, ValidationError
from backend.app.application.document._protocols import (
    ClassificationServiceProtocol,
    DocumentRepositoryProtocol,
)
from backend.app.models.document import Document
from backend.app.schemas.dto.document import (
    DocumentResponse,
    document_to_response,
)


async def reclassify_document(
    workspace_id: str,
    document_id: str,
    *,
    abs_path: Path,
    classification_base: Path,
    repo: DocumentRepositoryProtocol,
    classifier: ClassificationServiceProtocol,
) -> DocumentResponse:
    """Re-roda o classifier (regex + LLM) num único doc e grava o
    resultado. Operações de filesystem (resolver absolute path, renomear
    para o layout canônico) ficam no router/service composite — este
    use case só persiste o resultado da classificação.
    """
    doc = await repo.get_by_id(workspace_id, document_id)
    if doc is None:
        raise NotFoundError(
            "Documento não encontrado", code="document_not_found"
        )
    if not abs_path.exists():
        raise ValidationError(
            "Arquivo ausente no storage", code="stored_file_missing"
        )

    clf = classifier.classify(abs_path, classification_base)
    _apply_classification(doc, clf)
    return document_to_response(doc)


def _apply_classification(doc: Document, clf: dict) -> None:
    doc.doc_type = clf["doc_type"]
    doc.bank_code = clf.get("bank_code")
    doc.period = clf.get("period")
    doc.classification_confidence = clf.get("confidence")
    doc.needs_review = bool(clf.get("needs_review"))
    meta = dict(clf.get("classification_meta") or {})
    meta["reclassified_at"] = datetime.now(timezone.utc).isoformat()
    doc.classification_meta = meta
