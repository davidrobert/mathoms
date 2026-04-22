"""Backfill content_hash for Documents that were uploaded before dedupe existed.

Run this BEFORE applying the UNIQUE index migration on (workspace_id, content_hash)
— although the index is partial (WHERE content_hash IS NOT NULL) so it won't
fail if some rows are left NULL, the dedupe check only works for rows that
have a hash.

Usage:
    .venv/bin/python -m backend.app.scripts.backfill_content_hash --dry-run
    .venv/bin/python -m backend.app.scripts.backfill_content_hash --apply

``stored_path`` no DB pode ser relativo ao tenant — a resolução é feita via
:class:`~backend.app.services.storage.StorageService`.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import sys
from pathlib import Path

from sqlalchemy import select

from backend.app.core.database import async_session as AsyncSessionLocal
from backend.app.models.document import Document
from backend.app.services.storage import StorageService


def _sha256_of(path: Path) -> str | None:
    try:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except (OSError, FileNotFoundError):
        return None


_storage = StorageService()


async def backfill(apply: bool) -> tuple[int, int, int]:
    """Return (total_missing, hashed_ok, hash_failed)."""
    total = ok = failed = 0
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Document).where(Document.content_hash.is_(None)))
        docs = list(result.scalars().all())
        total = len(docs)
        print(f"[info] {total} documents without content_hash", flush=True)

        for doc in docs:
            if not doc.stored_path:
                failed += 1
                print(f"  [skip] {doc.id}: stored_path is NULL", flush=True)
                continue
            path = _storage.abs_stored_file(doc.workspace_id, doc.stored_path)
            if path is None:
                failed += 1
                print(
                    f"  [skip] {doc.id}: stored_path not resolvable — {doc.stored_path!r}",
                    flush=True,
                )
                continue
            digest = _sha256_of(path)
            if digest is None:
                failed += 1
                print(f"  [fail] {doc.id}: file not readable — {path}", flush=True)
                continue
            ok += 1
            if apply:
                doc.content_hash = digest
            print(
                f"  [ok]   {doc.id[:8]} {path.name[:60]:<60} sha256={digest[:12]}...",
                flush=True,
            )

        if apply:
            await db.commit()
            print(f"\n[done] committed {ok} hashes", flush=True)
        else:
            print(f"\n[dry-run] would commit {ok} hashes (use --apply)", flush=True)

    return total, ok, failed


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry-run", action="store_true", help="Show what would happen")
    g.add_argument("--apply", action="store_true", help="Actually write to DB")
    args = ap.parse_args()

    total, ok, failed = asyncio.run(backfill(apply=args.apply))
    print(f"\nTotal: {total}  Hashed: {ok}  Failed: {failed}")
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
