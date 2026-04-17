"""Fuzzy duplicate pointers for documents (same type + institution + period)."""

from __future__ import annotations

from backend.app.models.document import Document, DocumentType


def rebuild_fuzzy_duplicate_pointers(docs: list[Document]) -> int:
    """Recompute ``possible_duplicate_of_id`` for a document set (typically one workspace).

    For each triple (doc_type, bank_code, period) with at least two non-``other``
    documents, points every newer row at the oldest upload. Mutates ORM instances;
    caller commits.

    Returns the number of rows whose ``possible_duplicate_of_id`` or ``needs_review`` changed.
    """
    groups: dict[tuple, list[Document]] = {}
    for d in docs:
        if (
            d.doc_type
            and d.doc_type != DocumentType.other
            and d.bank_code
            and d.period
        ):
            key = (d.workspace_id, d.doc_type, d.bank_code, d.period)
            groups.setdefault(key, []).append(d)

    flagged = 0
    for group in groups.values():
        if len(group) < 2:
            continue
        group.sort(key=lambda x: x.uploaded_at)
        oldest = group[0]
        for d in group[1:]:
            if d.possible_duplicate_of_id != oldest.id:
                d.possible_duplicate_of_id = oldest.id
                d.needs_review = True
                flagged += 1
    return flagged
