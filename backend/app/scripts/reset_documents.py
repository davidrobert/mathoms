"""Destructive reset: wipe Documents from DB and tenant storage.

Use case: migração ou limpeza total. Uploads atuais guardam ``stored_path``
relativo a ``storage/<workspace_id>/`` (ex.: ``data/financial_statements/...-0_original.pdf``).
Este script não resolve ficheiros por linha — apaga todas as linhas ``documents``
e remove diretórios de dados por tenant (inbox, data, processed, etc.).

What it does (with --apply):
    1. DELETE FROM documents  (all rows, all workspaces)
    2. For each tenant dir storage/<ws-uuid>/:
         - remove: inbox/, inbox_processed/, data/, processed/, output/,
                   members/, logs/, _scratch/
         - PRESERVE: config/  (tenant-specific customizations)

Irreversible. Always start with --dry-run.

Usage:
    .venv/bin/python -m backend.app.scripts.reset_documents --dry-run
    .venv/bin/python -m backend.app.scripts.reset_documents --apply
"""

from __future__ import annotations

import argparse
import asyncio
import shutil
import sys
from pathlib import Path

from sqlalchemy import delete, func, select

from backend.app.core.config import settings
from backend.app.core.database import async_session as AsyncSessionLocal
from backend.app.models.document import Document
from backend.app.models.pipeline_artifact import PipelineArtifact

PRESERVE_DIRS = {"config"}
WIPE_DIRS = {
    "inbox",
    "inbox_processed",
    "data",
    "processed",
    "output",
    "members",
    "logs",
    "_scratch",
}


def _storage_root() -> Path:
    # settings.STORAGE_ROOT is the same value used by StorageService
    return Path(settings.STORAGE_ROOT)


def _du(path: Path) -> int:
    """Return total bytes of path (0 if missing)."""
    if not path.exists():
        return 0
    total = 0
    for p in path.rglob("*"):
        try:
            if p.is_file():
                total += p.stat().st_size
        except OSError:
            pass
    return total


def _human(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}TB"


async def reset(apply: bool) -> int:
    total_docs = 0
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(func.count(Document.id)))
        total_docs = int(result.scalar_one())
        print(f"[info] {total_docs} documents in DB will be deleted", flush=True)

        total_artifacts = int(
            (await db.execute(select(func.count(PipelineArtifact.id)))).scalar_one()
        )
        print(
            f"[info] {total_artifacts} pipeline_artifacts in DB will be deleted (Fase 4.2)",
            flush=True,
        )

        if apply:
            await db.execute(delete(PipelineArtifact))
            await db.execute(delete(Document))
            await db.commit()
            print("[done] documents + pipeline_artifacts deleted from DB", flush=True)

    root = _storage_root()
    if not root.exists():
        print(f"[warn] storage root {root} does not exist", flush=True)
        return 0

    total_freed = 0
    tenants = [p for p in root.iterdir() if p.is_dir()]
    print(f"\n[info] {len(tenants)} tenant directories found under {root}", flush=True)

    for tenant in sorted(tenants):
        print(f"\n  tenant {tenant.name}:", flush=True)
        for child in sorted(tenant.iterdir()):
            if not child.is_dir():
                continue
            if child.name in PRESERVE_DIRS:
                print(f"    [keep]   {child.name}/", flush=True)
                continue
            if child.name not in WIPE_DIRS:
                # Unknown dir — be cautious, just skip
                print(f"    [skip?]  {child.name}/  (unexpected name)", flush=True)
                continue
            size = _du(child)
            total_freed += size
            print(f"    [wipe]   {child.name}/  ({_human(size)})", flush=True)
            if apply:
                shutil.rmtree(child)
                child.mkdir()  # recreate empty so app paths still resolve

    print(f"\nTotal docs deleted: {total_docs}")
    print(f"Total storage freed: {_human(total_freed)}")
    if not apply:
        print("\n[dry-run] no changes made. Re-run with --apply to execute.")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry-run", action="store_true", help="Show what would happen")
    g.add_argument("--apply", action="store_true", help="Actually delete (IRREVERSIBLE)")
    args = ap.parse_args()
    sys.exit(asyncio.run(reset(apply=args.apply)))


if __name__ == "__main__":
    main()
