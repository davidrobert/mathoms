"""After a pipeline run, mark each document with E2 extract presence."""

from __future__ import annotations

import re
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

from sqlalchemy import select

from backend.app.core.database import SyncSessionLocal
from backend.app.models.document import Document, DocumentStatus


def _e2_json_name(source_filename: str) -> str:
    """Mirror ``scripts.e2_extract.make_output_name`` (avoid importing E2 stack)."""
    return re.sub(
        r"(-0_original)?\.(pdf|csv|xls|xlsx|jpg|jpeg|png)$",
        "-2_extract.json",
        source_filename,
        flags=re.IGNORECASE,
    )


def apply_pipeline_e2_sync_to_documents(
    documents: Sequence[Document],
    tenant_root: Path,
    completed_at: datetime,
) -> None:
    """Update pipeline timestamps, E2 flags, and promote ``ready`` → ``processed``.

    Called after a successful pipeline run. Idempotent for rows already ``processed``.
    """
    e2_dir = tenant_root / "processed" / "E2_extracts"
    e2_dir.mkdir(parents=True, exist_ok=True)

    for doc in documents:
        fname = Path(doc.stored_path or "").name
        if not fname:
            continue
        out_name = _e2_json_name(fname)
        has_extract = (e2_dir / out_name).exists()
        doc.pipeline_last_run_at = completed_at
        doc.pipeline_e2_extract_ok = has_extract
        if doc.status == DocumentStatus.ready:
            doc.status = DocumentStatus.processed


def sync_documents_pipeline_e2_status(
    workspace_id: str,
    tenant_root: Path,
    completed_at: datetime,
) -> None:
    """Set ``pipeline_last_run_at`` and ``pipeline_e2_extract_ok`` for workspace docs.

    A document is considered to have an E2 extract if ``processed/E2_extracts/<stem>-2_extract.json``
    exists, where ``stem`` is derived from the inbox filename (same convention as E2).

    Documents in ``ready`` are transitioned to ``processed`` (pipeline concluiu para o workspace).
    """
    with SyncSessionLocal() as db:
        rows = db.execute(
            select(Document).where(
                Document.workspace_id == workspace_id,
                Document.stored_path.isnot(None),
                Document.status != DocumentStatus.error,
            )
        ).scalars().all()

        apply_pipeline_e2_sync_to_documents(rows, tenant_root, completed_at)

        db.commit()
