"""Stage wrapper for E4 Categorization (ADR-097).

Chama ``scripts.e4_categorize.main_with_store(ctx)`` que opera direto sobre
``ctx.get_artifact_store()`` (Disk em CLI, DB em Web).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pipeline.context import WorkspaceContext


def run(ctx: "WorkspaceContext") -> dict:
    from pipeline.live_progress import emit_item_progress
    from scripts.e4_categorize import main_with_store

    emit_item_progress(
        ctx.pipeline_run_id,
        "E4",
        current_item="Categorização de transações",
        items_done=0,
        items_total=1,
        phase="preparing",
    )

    result = main_with_store(ctx)

    emit_item_progress(
        ctx.pipeline_run_id,
        "E4",
        current_item=None,
        items_done=1,
        items_total=1,
        phase="finalizing",
    )
    return result
