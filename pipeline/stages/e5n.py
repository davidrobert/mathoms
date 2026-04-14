"""Stage wrapper for E5.N Narrativas."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pipeline.context import WorkspaceContext


def run(ctx: WorkspaceContext) -> dict:
    """Executa E5.N narrativas com contexto injetado."""
    from scripts.e5n_narrativas import main as e5n_main
    result = e5n_main(root_dir=ctx.root)

    return {"success": bool(result)}
