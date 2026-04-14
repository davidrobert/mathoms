"""Stage wrapper for E0 Audit (integrity checks)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pipeline.context import WorkspaceContext


def run(ctx: WorkspaceContext) -> dict:
    """Executa E0 audit com contexto injetado."""
    from scripts.e0_audit import main as e0_audit_main
    e0_audit_main(root_dir=ctx.root)

    return {"success": True}
