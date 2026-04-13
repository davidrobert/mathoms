"""Stage wrapper for E0 Route (inbox routing)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pipeline.context import WorkspaceContext


def run(ctx: WorkspaceContext) -> dict:
    """Executa E0 route com contexto injetado."""
    from scripts.e0_route import main as e0_route_main
    e0_route_main(root_dir=ctx.root)

    return {"success": True}
