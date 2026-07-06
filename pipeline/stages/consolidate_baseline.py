"""Stage wrapper for E1.5c Consolidate — **Caminho B** (ADR-104, Sessão A5f).

Chama ``scripts.e15_consolidate.main_with_store(ctx)`` direto, sem bridge.
Lê e escreve baseline patrimonial via ``ctx.get_artifact_store()``.

``main(root_dir)`` legado coexiste no script para CLI direto e testes legados.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pipeline.context import WorkspaceContext


def run(ctx: "WorkspaceContext") -> dict:
    from pipeline.live_progress import emit_item_progress
    from scripts.e15_consolidate import main_with_store

    emit_item_progress(
        ctx.pipeline_run_id,
        "consolidate_baseline",
        current_item="Patrimônio inicial",
        items_done=0,
        items_total=1,
        phase="preparing",
    )

    result = main_with_store(ctx)

    emit_item_progress(
        ctx.pipeline_run_id,
        "consolidate_baseline",
        current_item=None,
        items_done=1,
        items_total=1,
        phase="finalizing",
    )
    return result
