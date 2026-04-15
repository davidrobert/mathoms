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
    """Aplica review LLM ao E5 JSON.

    Skips gracefully if no E7-review output exists (free tier: E7-review LLM
    is skipped, so there is nothing to apply).
    """
    review_dir = ctx.root / "processed" / "E7_review"
    if not review_path and (not review_dir.exists() or not list(review_dir.glob("*.json"))):
        return {"success": True, "skipped": True, "reason": "No E7-review output — E7-review not run (free tier)"}

    import sys
    if review_path:
        sys.argv = ["e7_review.py", "--apply", review_path]
    from scripts.e7_review import main as e7_main
    e7_main(root_dir=ctx.root)
    return {"success": True, "stage": "E7-apply"}
