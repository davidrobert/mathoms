"""After a pipeline run, mark each document with E2 extract presence."""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

from sqlalchemy import select

from backend.app.core.database import SyncSessionLocal
from backend.app.models.document import Document, DocumentStatus

# These doc type values are never processed by the deterministic E2 extractor —
# they live in income_tax_br/ or members/ and have no *-2_extract.json output.
# Using raw strings to avoid SQLAlchemy enum vs str comparison edge cases.
_NO_E2_EXTRACT_TYPE_VALUES = {"irpf", "e1_members_json", "e1_5_baseline_json"}


def _e2_json_name(source_filename: str) -> str:
    """Mirror ``scripts.e2_extract.make_output_name`` (avoid importing E2 stack)."""
    return re.sub(
        r"(-0_original)?\.(pdf|csv|xls|xlsx|jpg|jpeg|png)$",
        "-2_extract.json",
        source_filename,
        flags=re.IGNORECASE,
    )


def _find_e2_extract(e2_dir: Path, source_filename: str) -> Path | None:
    """Return the E2 extract Path for the given source filename, or None.

    Handles the case where E0 route renamed the file by appending an ``a``/``b``
    suffix (e.g. ``wise_extratoconta_2025-0_original.pdf`` →
    ``wise_extratoconta_2025a-0_original.pdf``) but the DB ``stored_path`` still
    holds the pre-rename name.  When the exact extract is missing we look for any
    extract whose stem matches the base stem + a single lowercase letter.
    """
    exact = e2_dir / _e2_json_name(source_filename)
    if exact.exists():
        return exact

    # Fuzzy: check for a/b/c… variants produced by E0 route disambiguation
    base_stem = re.sub(
        r"(-0_original)?\.(pdf|csv|xls|xlsx|jpg|jpeg|png)$",
        "",
        source_filename,
        flags=re.IGNORECASE,
    )
    pattern = re.compile(
        rf"^{re.escape(base_stem)}[a-z]-2_extract\.json$",
        re.IGNORECASE,
    )
    for f in e2_dir.iterdir():
        if f.is_file() and pattern.match(f.name):
            return f
    return None


def _read_extract_notes(extract_path: Path) -> str | None:
    """Read the ``notas`` array from an E2 extract JSON and return as newline-joined text.

    Returns None when there are no notes or the file cannot be parsed.
    """
    try:
        data = json.loads(extract_path.read_text(encoding="utf-8"))
        notes = data.get("notas") or []
        if not notes:
            return None
        return "\n".join(str(n) for n in notes if n)
    except Exception:
        return None


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

        doc.pipeline_last_run_at = completed_at

        # IRPF and member JSON types are not processed by the deterministic E2
        # extractor — clear any stale extract flag so they don't show as "Sem extrato".
        doc_type_val = doc.doc_type.value if hasattr(doc.doc_type, "value") else str(doc.doc_type or "")
        if doc_type_val in _NO_E2_EXTRACT_TYPE_VALUES:
            doc.pipeline_e2_extract_ok = None
            doc.pipeline_extract_notes = None
            if doc.status == DocumentStatus.ready:
                doc.status = DocumentStatus.processed
            continue

        extract_path = _find_e2_extract(e2_dir, fname)
        doc.pipeline_e2_extract_ok = extract_path is not None
        doc.pipeline_extract_notes = _read_extract_notes(extract_path) if extract_path else None
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
