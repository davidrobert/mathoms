"""Stage wrapper for E6 Report Rendering."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pipeline.context import WorkspaceContext


def run(ctx: WorkspaceContext) -> dict:
    """Executa E6 rendering com contexto injetado."""
    from scripts.e6_render import render_report
    output_path = render_report(root_dir=ctx.root)

    return {
        "success": True,
        "output_path": str(output_path) if output_path else None,
    }
