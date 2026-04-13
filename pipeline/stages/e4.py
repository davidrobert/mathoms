"""Stage wrapper for E4 Categorization."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pipeline.context import WorkspaceContext


def run(ctx: WorkspaceContext) -> dict:
    """Executa E4 categorization com contexto injetado."""
    from scripts.e4_categorize import main as e4_main
    e4_main(root_dir=ctx.root)

    files = [f.name for f in sorted(ctx.e4_dir.glob("*-4_unified.json"))]
    return {"success": True, "files_created": files, "total": len(files)}
