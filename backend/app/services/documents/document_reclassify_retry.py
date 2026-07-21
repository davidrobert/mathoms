"""Retry SÍNCRONO de docs parkados por skip LLM transitório (C8 · ADR-329).

Espelho síncrono de ``reclassify`` — gevent-safe (sem ``asyncio``; ``asyncio.run()``
crasha no worker, ver ``pipeline_task._persist_aggregate_suggestions``). Reusa os
primitivos SÍNCRONOS de classificação/rota. Roda no início de um run premium para
trazer de volta ao corpus docs que ficaram em ``needs_review`` por ``missing_api_key``.

A37.l3 fecha as duas quebras que deixavam docs parkados para sempre:
``stored_path`` stale (arquivo movido para ``inbox_processed/``) é relocado por
``content_hash`` antes do retry, e a API key é resolvida com paridade ao parecer
(``llm_config`` DB-backed → env), não só de ``os.environ``.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
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
from backend.app.services.documents.stored_path_selfheal import StoredPathSelfHealer
from backend.app.services.storage import StorageService

logger = logging.getLogger("mathoms.documents.reclassify_retry")


def _resolve_llm_api_key(workspace_id: str, db: Session) -> str | None:
    """Paridade com o parecer: ``llm_config`` DB-backed → env (A37.l3) — o gate
    env-only parkava docs p/ sempre em worker sem a env var, enquanto os stages
    LLM (que leem ``llm_config``) funcionavam normalmente."""
    from backend.app.services.config_materializer import serialize_llm_config

    cfg = serialize_llm_config(workspace_id, db)
    if isinstance(cfg, dict) and cfg.get("api_key"):
        return cfg["api_key"]
    return os.environ.get("ANTHROPIC_API_KEY") or None


def _route_confident_to_data(doc: Document, clf: dict, abs_path, tenant_root: Path) -> None:
    """Move o arquivo para ``data/`` sob o nome canônico (só p/ classificação confiante)."""
    rename_result = rename_to_canonical(
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
    if rename_result is not None:
        # Sem isso o stored_path fica stale de novo — exatamente o drift que a
        # relocação por content_hash corrige (A37.l3; paridade com o bulk).
        abs_new, rel_new = rename_result
        doc.stored_path = rel_new
        doc.original_name = abs_new.name


def _locate_parked_file(
    doc: Document, storage: StorageService, healer: StoredPathSelfHealer
) -> tuple[Path | None, bool]:
    """``(path atual, relocated)`` — reloca stored_path stale via content_hash (A37.l3)."""
    abs_path = (
        storage.abs_stored_file(doc.workspace_id, doc.stored_path) if doc.stored_path else None
    )
    if abs_path is not None and abs_path.exists():
        return abs_path, False
    found = healer.relocate(doc)
    return found, found is not None


@dataclass(frozen=True, slots=True)
class _RetryRunContext:
    base: Path
    storage: StorageService
    tenant_root: Path
    healer: StoredPathSelfHealer
    api_key: str


def _retry_one_parked(doc: Document, rc: _RetryRunContext) -> tuple[str, bool]:
    """Re-classifica 1 doc parkado → ``(no_file | reclassified | routed, relocated)``."""
    abs_path, relocated = _locate_parked_file(doc, rc.storage, rc.healer)
    if abs_path is None:
        return "no_file", False
    clf = classify_document(abs_path, rc.base, api_key=rc.api_key)
    _apply_classification(doc, clf)
    if not classification_can_route_to_data(clf):
        return "reclassified", relocated
    _route_confident_to_data(doc, clf, abs_path, rc.tenant_root)
    return "routed", relocated


def _count_retry_result(stats: dict[str, int], result: str, relocated: bool) -> None:
    if relocated:
        stats["relocated"] += 1
    if result == "no_file":
        stats["no_file"] += 1
        return
    stats["retried"] += 1
    stats["reclassified"] += 1
    if result == "routed":
        stats["routed"] += 1


_RETRY_STAT_KEYS = (
    "scanned",
    "retried",
    "reclassified",
    "routed",
    "no_file",
    "skipped",
    "relocated",
)


def _retry_each_parked(
    db: Session, workspace_id: str, stats: dict[str, int], rc: _RetryRunContext
) -> None:
    query = select(Document).where(
        Document.workspace_id == workspace_id, Document.needs_review.is_(True)
    )
    for doc in db.execute(query).scalars().all():
        if not is_retriable_skip_reason(doc.classification_meta):
            stats["skipped"] += 1
            continue
        stats["scanned"] += 1
        _count_retry_result(stats, *_retry_one_parked(doc, rc))


def retry_parked_documents_sync(
    workspace_id: str, *, db: Session, storage: StorageService, tenant_root: Path
) -> dict[str, int]:
    """Re-classifica docs ``needs_review`` parkados por skip transitório e roteia os confiantes para ``data/`` (C8/ADR-329 + A37.l3). Caller comita."""
    stats = dict.fromkeys(_RETRY_STAT_KEYS, 0)
    api_key = _resolve_llm_api_key(workspace_id, db)
    if api_key is None:
        logger.info("reclassify_retry_skipped_no_llm_key workspace_id=%s", workspace_id)
        return stats
    rc = _RetryRunContext(
        base=resolve_classification_base(settings.PIPELINE_ROOT / "config", tenant_root),
        storage=storage,
        tenant_root=tenant_root,
        healer=StoredPathSelfHealer(storage.tenant_root(workspace_id)),
        api_key=api_key,
    )
    _retry_each_parked(db, workspace_id, stats, rc)
    return stats
