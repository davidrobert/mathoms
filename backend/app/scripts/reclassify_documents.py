"""Reclassify all Documents using the content-first classifier.

Walks the ``documents`` table, reads ``stored_path`` for each row, and re-runs
``classify_document()`` — which since the content-first rewrite no longer uses
filenames. Updates ``doc_type``, ``bank_code``, ``period``,
``classification_meta``, ``classification_confidence``, ``needs_review``.

Also rebuilds ``possible_duplicate_of_id`` pointers across the workspace after
reclassification, since doc_type/bank_code/period may have changed.

Per decision D3=B, the prior ``classification_meta`` is OVERWRITTEN (not
preserved). If you need an audit trail, take a DB backup before running with
--apply.

Usage:
    .venv/bin/python -m backend.app.scripts.reclassify_documents --dry-run
    .venv/bin/python -m backend.app.scripts.reclassify_documents --apply
    .venv/bin/python -m backend.app.scripts.reclassify_documents --apply --no-llm
    .venv/bin/python -m backend.app.scripts.reclassify_documents --apply \\
        --only-doc-type other           # restrict to currently-misclassified docs

Caminhos: ``stored_path`` relativo ao workspace é resolvido com
:class:`~backend.app.services.storage.StorageService` (compatível com legado absoluto).
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

from sqlalchemy import select

from backend.app.core.config import settings
from backend.app.core.database import async_session as AsyncSessionLocal
from backend.app.models.document import Document, DocumentStatus, DocumentType
from backend.app.services.document_processor import (
    _detect_json_type,
    classify_document,
)
from backend.app.services.storage import StorageService


def _doc_type_value(v) -> str:
    return v.value if hasattr(v, "value") else (v or "")


_storage = StorageService()


async def _reclassify_one(doc: Document, config_root: Path) -> dict:
    path = _storage.abs_stored_file(doc.workspace_id, doc.stored_path)
    if path is None or not path.exists():
        return {"skipped": "no_stored_path", "prior": _doc_type_value(doc.doc_type)}

    # JSON members/baseline take a dedicated code path (same as upload flow).
    if path.suffix.lower() == ".json":
        json_type = _detect_json_type(path)
        if json_type:
            return {
                "prior": _doc_type_value(doc.doc_type),
                "new": json_type.value,
                "bank_code": None,
                "period": None,
                "confidence": 1.0,
                "needs_review": False,
                "dest_group": None,
                "meta": {"source": "json_structure", "type": json_type.value},
            }

    try:
        result = classify_document(path, config_root)
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {str(exc)[:200]}"}

    return {
        "prior": _doc_type_value(doc.doc_type),
        "new": _doc_type_value(result["doc_type"]),
        "bank_code": result["bank_code"],
        "period": result["period"],
        "confidence": result.get("confidence"),
        "needs_review": result.get("needs_review"),
        "dest_group": result.get("dest_group"),
        "meta": result["classification_meta"],
    }


async def _rebuild_fuzzy_duplicates(db, docs: list[Document]) -> int:
    """After reclassification, recompute possible_duplicate_of_id.

    For each doc with a non-"other" type + bank + period, point it at the
    OLDEST other doc in the same workspace with the same triple. Oldest wins
    so the flagged doc is always the "new" one.
    """
    # Group by (workspace_id, doc_type, bank_code, period)
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


async def reclassify(apply: bool, use_llm: bool, only_doc_type: str | None) -> int:
    if not use_llm:
        # Strongest opt-out: remove the key so classify_by_llm returns None.
        os.environ.pop("ANTHROPIC_API_KEY", None)

    config_root = settings.PIPELINE_ROOT  # base_dir that has /config/

    changed = preserved = errored = skipped = 0
    changed_by_type: dict[str, int] = {}

    async with AsyncSessionLocal() as db:
        query = select(Document).where(Document.status != DocumentStatus.error)
        if only_doc_type:
            query = query.where(Document.doc_type == only_doc_type)
        result = await db.execute(query)
        docs = list(result.scalars().all())
        print(f"[info] {len(docs)} documents to consider", flush=True)

        for doc in docs:
            info = await _reclassify_one(doc, config_root)
            if "skipped" in info:
                skipped += 1
                continue
            if "error" in info:
                errored += 1
                print(f"  [err]  {doc.id[:8]} — {info['error']}", flush=True)
                continue

            prior = info["prior"]
            new = info["new"]
            changed_flag = (prior != new) or (
                doc.bank_code != info["bank_code"] or doc.period != info["period"]
            )
            if changed_flag:
                changed += 1
                changed_by_type[new] = changed_by_type.get(new, 0) + 1
                print(
                    f"  [upd]  {doc.id[:8]} {doc.original_name[:50]:<50} "
                    f"{prior or 'NULL':>16} -> {new:<16} "
                    f"conf={info['confidence']:.2f} bank={info['bank_code']} "
                    f"period={info['period']}",
                    flush=True,
                )
            else:
                preserved += 1

            if apply:
                doc.doc_type = info["new"] or None
                doc.bank_code = info["bank_code"]
                doc.period = info["period"]
                doc.classification_meta = info["meta"]
                doc.classification_confidence = info["confidence"]
                doc.needs_review = bool(info["needs_review"])

        if apply:
            # Rebuild fuzzy duplicate pointers across the refreshed classification
            flagged = await _rebuild_fuzzy_duplicates(db, docs)
            print(f"[info] flagged {flagged} fuzzy duplicates", flush=True)
            await db.commit()
            print("[done] committed reclassification", flush=True)
        else:
            print("[dry-run] no writes (use --apply)", flush=True)

    print(
        f"\nTotal: {len(docs)}  Changed: {changed}  Preserved: {preserved}  "
        f"Skipped: {skipped}  Errored: {errored}"
    )
    if changed_by_type:
        print("\nNew classification distribution (changed rows only):")
        for t, n in sorted(changed_by_type.items(), key=lambda x: -x[1]):
            print(f"  {t or 'NULL':<20} {n}")
    return 0 if errored == 0 else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry-run", action="store_true", help="Show what would change")
    g.add_argument("--apply", action="store_true", help="Actually write to DB")
    ap.add_argument(
        "--no-llm", action="store_true",
        help="Disable LLM fallback (regex only). Cheaper, less accurate."
    )
    ap.add_argument(
        "--only-doc-type", default=None,
        help="Restrict to documents currently classified as this type (e.g. 'other')."
    )
    args = ap.parse_args()

    rc = asyncio.run(reclassify(
        apply=args.apply,
        use_llm=not args.no_llm,
        only_doc_type=args.only_doc_type,
    ))
    sys.exit(rc)


if __name__ == "__main__":
    main()
