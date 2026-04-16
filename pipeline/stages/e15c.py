"""Stage wrapper for E1.5 Consolidate (baseline enrichment)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pipeline.context import WorkspaceContext


def run(ctx: WorkspaceContext) -> dict:
    """Executa E1.5 consolidate com contexto injetado.

    Skips gracefully if E1.5 baseline does not exist (free tier: E1.5 LLM is
    skipped, so there is nothing to consolidate — this is not an error).
    """
    baseline_input = ctx.e2_dir / "baseline_patrimonial-1.5_consolidated.json"
    raw_baseline = ctx.e2_dir / "baseline_patrimonial-1.5_baseline.json"

    if not baseline_input.exists() and not raw_baseline.exists():
        return {"success": True, "skipped": True, "reason": "No baseline file — E1.5 not run (free tier)"}

    from pipeline.live_progress import emit_stage_activity

    emit_stage_activity(
        ctx.pipeline_run_id,
        "E1.5c",
        message="Consolidando patrimônio inicial (enriquecimento determinístico)…",
    )

    from scripts.e15_consolidate import main as e15c_main
    e15c_main(root_dir=ctx.root)

    return {"success": True, "baseline_exists": baseline_input.exists()}
