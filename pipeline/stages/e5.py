"""Stage wrapper for E5 Analysis."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pipeline.context import WorkspaceContext


def run(ctx: WorkspaceContext) -> dict:
    """Executa E5 analysis com contexto injetado."""
    from scripts.e5_analyze import main as e5_main
    e5_main(root_dir=ctx.root)

    output = ctx.e5_dir / "analise_financeira-5_analysis.json"
    return {"success": True, "output_exists": output.exists()}
