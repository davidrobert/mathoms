"""Stage wrapper for E7 Review & Cross-validation."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pipeline.context import WorkspaceContext


def run_crossval(ctx: WorkspaceContext) -> dict:
    """Executa E7 cross-validation com contexto injetado."""
    from scripts.e7_review import main as e7_main
    e7_main(root_dir=ctx.root)
    return {"success": True, "stage": "E7-crossval"}


def run_apply(ctx: WorkspaceContext, review_path: str = None) -> dict:
    """Aplica review LLM ao E5 JSON."""
    import sys
    if review_path:
        sys.argv = ["e7_review.py", "--apply", review_path]
    from scripts.e7_review import main as e7_main
    e7_main(root_dir=ctx.root)
    return {"success": True, "stage": "E7-apply"}
