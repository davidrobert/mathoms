"""Use case: correção manual de classificação (manual_override)."""

from __future__ import annotations

from datetime import datetime, timezone

from backend.app.application.base.errors import NotFoundError, ValidationError
from backend.app.application.document._protocols import (
    DocumentRepositoryProtocol,
)
from backend.app.models.document import DocumentStatus
from backend.app.schemas.dto.document import (
    DocumentResponse,
    DocumentUpdateCommand,
    document_to_response,
)

# Campos que afetam qual parser/LLM é usado na extração E2 — mudança
# invalida o extrato anterior e recoloca o doc na fila do pipeline.
_EXTRACTION_AFFECTING: frozenset[str] = frozenset({"doc_type", "bank_code"})


async def update_document_classification(
    cmd: DocumentUpdateCommand,
    *,
    workspace_id: str,
    document_id: str,
    updated_by: str,
    repo: DocumentRepositoryProtocol,
) -> DocumentResponse:
    """Aplica overrides do usuário e marca ``classification_meta.manual_override``.
    Zera ``needs_review`` (o usuário confirmou) e invalida o extrato E2 anterior
    se ``doc_type``/``bank_code`` mudou.
    """
    updates = cmd.model_dump(exclude_unset=True)
    if not updates:
        raise ValidationError("Nenhum campo para atualizar", code="empty_update")

    doc = await repo.get_by_id(workspace_id, document_id)
    if doc is None:
        raise NotFoundError("Documento não encontrado", code="document_not_found")

    for field in ("doc_type", "bank_code", "period"):
        if field in updates:
            setattr(doc, field, updates[field])

    meta = dict(doc.classification_meta or {})
    meta["manual_override"] = {
        "at": datetime.now(timezone.utc).isoformat(),
        "by": updated_by,
        "fields": sorted(updates.keys()),
    }
    doc.classification_meta = meta
    doc.classification_confidence = 1.0
    doc.needs_review = False

    if updates.keys() & _EXTRACTION_AFFECTING:
        doc.pipeline_last_run_at = None
        doc.pipeline_e2_extract_ok = None
        if doc.status == DocumentStatus.processed:
            doc.status = DocumentStatus.ready

    return document_to_response(doc)
