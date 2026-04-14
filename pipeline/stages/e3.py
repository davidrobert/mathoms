"""Stage wrapper for E3 Reconciliation."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pipeline.context import WorkspaceContext


def run(ctx: WorkspaceContext) -> dict:
    """Executa E3 reconciliation com contexto injetado."""
    from scripts.e3_reconcile import main as e3_main
    e3_main(root_dir=ctx.root)

    files = [f.name for f in sorted(ctx.e3_dir.glob("*-3_reconciled.json"))]
    return {"success": True, "files_created": files, "total": len(files)}
