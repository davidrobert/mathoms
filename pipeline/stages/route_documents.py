"""Stage wrapper for E0 Route (inbox routing)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pipeline.context import WorkspaceContext


def run(ctx: WorkspaceContext) -> dict:
    """Executa E0 route com contexto injetado.

    Mapeamento de stats → resultado do stage:
      - ``error`` em stats → RuntimeError (orquestrador trata como falha)
      - ``unidentified > 0`` → success com warning (não interrompe pipeline)
      - caso contrário → success
    """
    from scripts.e0_route import _init_config, route_all

    _init_config(ctx.root)
    stats = route_all(
        base=ctx.root,
        dry_run=False,
        use_llm=True,
        pipeline_run_id=ctx.pipeline_run_id,
    )

    if stats.get("error"):
        raise RuntimeError(f"E0 route failed: {stats['error']}")

    if stats.get("unidentified", 0) > 0:
        return {
            "success": True,
            "warning": "1 ou mais documentos não identificados permanecerão no inbox para revisão manual.",
        }

    return {"success": True}
