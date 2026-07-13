"""Retry SÍNCRONO de docs parkados por skip LLM transitório (C8 · ADR-329).

Espelho síncrono de ``reclassify`` — gevent-safe (sem ``asyncio``; ``asyncio.run()``
crasha no worker, ver ``pipeline_task._persist_aggregate_suggestions``). Reusa os
primitivos SÍNCRONOS de classificação/rota. Roda no início de um run premium para
trazer de volta ao corpus docs que ficaram em ``needs_review`` por ``missing_api_key``.
"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.models.document import Document
from backend.app.services.documents.canonical_routing import rename_to_canonical
from backend.app.services.documents.document_classification import (
    classification_can_route_to_data,
    classify_document,
    is_retriable_skip_reason,
)
from backend.app.services.documents.document_processor import resolve_classification_base
from backend.app.services.documents.document_reclassify_bulk_service import _apply_classification
from backend.app.services.storage import StorageService


def _route_confident_to_data(doc: Document, clf: dict, abs_path, tenant_root: Path) -> None:
    """Move o arquivo para ``data/`` sob o nome canônico (só p/ classificação confiante)."""
    rename_to_canonical(
        abs_path,
        tenant_root,
        settings.PIPELINE_ROOT,
        dest_group=clf["dest_group"],
        e0_doc_type=clf["e0_doc_type"],
        institution=clf.get("bank_code"),
        period=clf.get("period"),
        classification_meta=doc.classification_meta,
        content_hash=doc.content_hash,
    )


def _retry_one_parked(doc: Document, *, base, storage: StorageService, tenant_root: Path) -> str:
    """Re-classifica 1 doc parkado → ``no_file`` | ``reclassified`` | ``routed`` (confiança baixa mantém needs_review, não roteia lixo)."""
    abs_path = (
        storage.abs_stored_file(doc.workspace_id, doc.stored_path) if doc.stored_path else None
    )
    if abs_path is None or not abs_path.exists():
        return "no_file"
    clf = classify_document(abs_path, base)
    _apply_classification(doc, clf)
    if not classification_can_route_to_data(clf):
        return "reclassified"
    _route_confident_to_data(doc, clf, abs_path, tenant_root)
    return "routed"


def retry_parked_documents_sync(
    workspace_id: str, *, db: Session, storage: StorageService, tenant_root: Path
) -> dict[str, int]:
    """Re-classifica docs ``needs_review`` parkados por skip transitório e roteia os confiantes para ``data/`` (C8/ADR-329). Caller comita."""
    base = resolve_classification_base(settings.PIPELINE_ROOT / "config", tenant_root)
    query = select(Document).where(
        Document.workspace_id == workspace_id, Document.needs_review.is_(True)
    )
    stats = {"scanned": 0, "reclassified": 0, "routed": 0}
    for doc in db.execute(query).scalars().all():
        if not is_retriable_skip_reason(doc.classification_meta):
            continue
        stats["scanned"] += 1
        result = _retry_one_parked(doc, base=base, storage=storage, tenant_root=tenant_root)
        if result in ("reclassified", "routed"):
            stats["reclassified"] += 1
        if result == "routed":
            stats["routed"] += 1
    return stats
