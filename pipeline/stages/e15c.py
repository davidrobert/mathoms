"""Stage wrapper for E1.5 Consolidate (baseline enrichment)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pipeline.context import WorkspaceContext


def run(ctx: WorkspaceContext) -> dict:
    """Executa E1.5 consolidate com contexto injetado."""
    from scripts.e15_consolidate import main as e15c_main
    e15c_main(root_dir=ctx.root)

    baseline = ctx.e2_dir / "baseline_patrimonial-1.5_consolidated.json"
    return {"success": True, "baseline_exists": baseline.exists()}
