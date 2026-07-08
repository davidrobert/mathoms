"""Composite: reclassify em lote de documentos do workspace (A6e.4 slice 10).

Extraído de ``api/documents.py::reclassify_documents``. Re-roda o
classifier (regex + LLM fallback) em cada doc que não tenha manual override,
aplica renomeação canônica quando o resultado é confiante, e rebuilds os
pointers de fuzzy dedup.

Não commita; router decide transação + audit.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import partial

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.models.document import Document, DocumentStatus
from backend.app.repositories.document_repository import DocumentRepository
from backend.app.services.artifact_tombstone import tombstone_e2_artifacts_for_document
from backend.app.services.canonical_routing import rename_to_canonical
from backend.app.services.classification_telemetry import emit_classification_outcome
from backend.app.services.config_materializer import ensure_tenant_pipeline_config
from backend.app.services.document_classification import (
    classification_can_route_to_data,
    classify_document,
)
from backend.app.services.document_duplicates import rebuild_fuzzy_duplicate_pointers
from backend.app.services.document_processor import (
    _detect_json_type,
    resolve_classification_base,
)
from backend.app.services.storage import StorageService


@dataclass(frozen=True, slots=True)
class ReclassifyBulkStats:
    total: int
    updated: int
    skipped: int
    errors: int


async def reclassify_workspace_documents(
    workspace_id: str,
    *,
    db: AsyncSession,
    repo: DocumentRepository,
    storage: StorageService,
    skip_manual_overrides: bool = True,
) -> ReclassifyBulkStats:
    """Reclassifica todos os docs do workspace. Caller comita + audita."""
    tenant_root = storage.ensure_tenant_dirs(workspace_id)
    ensure_tenant_pipeline_config(workspace_id, tenant_root)
    classification_base = resolve_classification_base(
        settings.PIPELINE_ROOT / "config", tenant_root
    )

    docs = await repo.list(workspace_id)
    total = len(docs)
    counters = _Counters()
    loop = asyncio.get_event_loop()

    for doc in docs:
        await _reclassify_one(
            doc,
            workspace_id=workspace_id,
            tenant_root=tenant_root,
            classification_base=classification_base,
            skip_manual_overrides=skip_manual_overrides,
            storage=storage,
            loop=loop,
            counters=counters,
            db=db,
        )

    dup_rows = await repo.list_non_error(workspace_id)
    rebuild_fuzzy_duplicate_pointers(dup_rows)

    return ReclassifyBulkStats(
        total=total,
        updated=counters.updated,
        skipped=counters.skipped,
        errors=counters.errors,
    )


class _Counters:
    __slots__ = ("updated", "skipped", "errors")

    def __init__(self) -> None:
        self.updated = 0
        self.skipped = 0
        self.errors = 0


async def _reclassify_one(
    doc: Document,
    *,
    workspace_id: str,
    tenant_root,
    classification_base,
    skip_manual_overrides: bool,
    storage: StorageService,
    loop,
    counters: _Counters,
    db: AsyncSession,
) -> None:
    if skip_manual_overrides and _has_manual_override(doc):
        counters.skipped += 1
        return

    if not doc.stored_path:
        counters.skipped += 1
        return

    abs_path = storage.abs_stored_file(doc.workspace_id, doc.stored_path)
    if abs_path is None or not abs_path.exists():
        counters.skipped += 1
        return

    try:
        prior_type = doc.doc_type
        prior_extraction_identity = _extraction_identity(doc)
        if abs_path.suffix.lower() == ".json":
            updated = _reclassify_json_by_structure(
                doc, abs_path, workspace_id=workspace_id, prior_type=prior_type
            )
            if updated:
                await _tombstone_if_extraction_changed(doc, prior_extraction_identity, db)
                counters.updated += 1
            else:
                counters.skipped += 1
            return

        clf = await loop.run_in_executor(
            None, partial(classify_document, abs_path, classification_base)
        )
        emit_classification_outcome(
            context="reclassify",
            classification=clf,
            workspace_id=workspace_id,
            prior_doc_type=prior_type,
            outcome="classified",
        )
        _apply_classification(doc, clf)
        await _maybe_rename_canonical(doc, clf, abs_path, tenant_root=tenant_root, loop=loop)
        await _tombstone_if_extraction_changed(doc, prior_extraction_identity, db)
        counters.updated += 1
    except Exception as exc:
        doc.error_message = f"Reclassify error: {str(exc)[:200]}"
        counters.errors += 1


def _extraction_identity(doc: Document) -> tuple[str | None, str | None]:
    """Par (doc_type, bank_code) normalizado — muda ⇒ extrato E2 antigo é inválido."""
    doc_type = doc.doc_type.value if hasattr(doc.doc_type, "value") else doc.doc_type
    return (doc_type, doc.bank_code)


async def _tombstone_if_extraction_changed(
    doc: Document, prior_identity: tuple[str | None, str | None], db: AsyncSession
) -> None:
    """ADR-311 D1 — reclassificação que muda ``doc_type``/``bank_code`` deleta
    os artifacts E2* do documento e recoloca-o na fila incremental; sem isso a
    key antiga persiste e envenena o E3 a cada run."""
    if _extraction_identity(doc) == prior_identity:
        return
    await tombstone_e2_artifacts_for_document(
        db,
        workspace_id=doc.workspace_id,
        document_id=doc.id,
        content_hash=doc.content_hash,
    )
    doc.pipeline_last_run_at = None
    doc.pipeline_e2_extract_ok = None


def _has_manual_override(doc: Document) -> bool:
    meta = doc.classification_meta or {}
    return isinstance(meta, dict) and "manual_override" in meta


def _reclassify_json_by_structure(
    doc: Document,
    abs_path,
    *,
    workspace_id: str,
    prior_type,
) -> bool:
    json_type = _detect_json_type(abs_path)
    if not json_type:
        return False
    doc.doc_type = json_type
    doc.classification_confidence = 1.0
    doc.needs_review = False
    doc.classification_meta = {"source": "json_structure", "reclassified": True}
    emit_classification_outcome(
        context="reclassify",
        classification={
            "doc_type": json_type,
            "confidence": 1.0,
            "needs_review": False,
            "classification_meta": doc.classification_meta,
        },
        workspace_id=workspace_id,
        prior_doc_type=prior_type,
        outcome="json_structure",
    )
    return True


def _apply_classification(doc: Document, clf: dict) -> None:
    doc.doc_type = clf["doc_type"]
    doc.bank_code = clf["bank_code"]
    doc.period = clf["period"]
    doc.classification_confidence = clf["confidence"]
    doc.needs_review = clf["needs_review"]
    meta = dict(clf.get("classification_meta") or {})
    meta["reclassified_at"] = datetime.now(timezone.utc).isoformat()
    doc.classification_meta = meta
    if doc.status == DocumentStatus.error:
        doc.status = DocumentStatus.ready
        doc.error_message = None


async def _maybe_rename_canonical(
    doc: Document,
    clf: dict,
    abs_path,
    *,
    tenant_root,
    loop,
) -> None:
    if not classification_can_route_to_data(clf):
        return
    meta = doc.classification_meta or {}
    rename_result = await loop.run_in_executor(
        None,
        partial(
            rename_to_canonical,
            abs_path,
            tenant_root,
            settings.PIPELINE_ROOT,
            dest_group=clf["dest_group"],
            e0_doc_type=clf["e0_doc_type"],
            institution=clf.get("bank_code"),
            period=clf.get("period"),
            classification_meta=meta,
            content_hash=doc.content_hash,
        ),
    )
    if rename_result is not None:
        abs_new, rel_new = rename_result
        doc.stored_path = rel_new
        doc.original_name = abs_new.name
