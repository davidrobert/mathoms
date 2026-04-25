"""Stage wrapper for E0 Unlock (PDF/ZIP decryption)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pipeline.context import WorkspaceContext


def run(ctx: WorkspaceContext) -> dict:
    """Executa E0 unlock com contexto injetado."""
    from scripts.e0_unlock import main as e0_unlock_main

    e0_unlock_main(root_dir=ctx.root)

    return {"success": True}
