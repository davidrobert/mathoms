"""Rename canônico de arquivo após PATCH manual de classificação (espelha bulk reclassify; evita "Sem extrato" por filename desalinhado pós-override)."""

from __future__ import annotations

import asyncio
from functools import partial
from pathlib import Path

from backend.app.core.config import settings
from backend.app.models.document import Document, DocumentType
from backend.app.services.canonical_routing import rename_to_canonical
from backend.app.services.document_classification import (
    document_type_to_e0_dest,
    map_e0_doc_type_to_document_type,
)
from backend.app.services.storage import StorageService

_RENAME_FIELDS = {"doc_type", "bank_code", "period"}


def _normalize_doc_type(value) -> DocumentType | None:
    if isinstance(value, str):
        try:
            return DocumentType(value)
        except ValueError:
            return None
    return value


def resolve_e0_for_rename(doc: Document) -> tuple[str, str] | None:
    """Preserva e0_doc_type do filename se ainda casa com o novo doc_type — senão usa canônico do reverse map."""
    new_dt = _normalize_doc_type(doc.doc_type)
    if new_dt is None:
        return None
    from scripts.route_documents import detect_doc_type as _detect_e0

    fname = (doc.stored_path or "").rsplit("/", 1)[-1]
    if fname:
        detected = _detect_e0(fname)
        if detected and map_e0_doc_type_to_document_type(detected[0]) == new_dt:
            return detected[0], detected[1]
    return document_type_to_e0_dest(new_dt)


def _build_rename_callable(
    doc: Document, abs_path: Path, tenant_root: Path, e0_dest: tuple[str, str]
):
    return partial(
        rename_to_canonical,
        abs_path,
        tenant_root,
        settings.PIPELINE_ROOT,
        dest_group=e0_dest[1],
        e0_doc_type=e0_dest[0],
        institution=doc.bank_code,
        period=doc.period,
        classification_meta=doc.classification_meta or {},
        content_hash=doc.content_hash,
    )


async def maybe_rename_after_manual_override(
    doc: Document, updates: dict, workspace_id: str, storage: StorageService
) -> None:
    """Renomeia arquivo após PATCH quando doc_type/bank_code/period mudou."""
    if not (updates.keys() & _RENAME_FIELDS) or not doc.stored_path:
        return
    abs_path = storage.abs_stored_file(workspace_id, doc.stored_path)
    if abs_path is None or not abs_path.exists():
        return
    e0_dest = resolve_e0_for_rename(doc)
    if e0_dest is None:
        return
    fn = _build_rename_callable(doc, abs_path, storage.tenant_root(workspace_id), e0_dest)
    rename_result = await asyncio.get_event_loop().run_in_executor(None, fn)
    if rename_result is not None:
        doc.stored_path = rename_result[1]
        doc.original_name = rename_result[0].name
