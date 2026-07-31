"""Stage wrapper for E0 Route (inbox routing)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from pipeline.context import WorkspaceContext


def run(ctx: WorkspaceContext) -> dict:
    """Executa E0 route com contexto injetado.

    Mapeamento de stats → resultado do stage:
      - ``error`` em stats → RuntimeError (orquestrador trata como falha)
      - ``unidentified > 0`` → success com warning (não interrompe pipeline)
      - caso contrário → success
    """
    from scripts.route_documents import _init_config, route_all

    _init_config(ctx.root)
    stats = route_all(
        base=ctx.root,
        dry_run=False,
        # ADR-355: o fallback LLM de classificação (ADR-081 camada 2) é chamada
        # condicional dentro de stage não-`is_llm` — `skip_llm` não a alcança
        # pela lista de stages, só por esta política.
        use_llm=ctx.llm_calls_allowed,
        pipeline_run_id=ctx.pipeline_run_id,
    )

    if stats.get("error"):
        raise RuntimeError(f"E0 route failed: {stats['error']}")

    return _stage_detail(ctx, stats)


def _stage_detail(ctx: WorkspaceContext, stats: dict) -> dict:
    """Resultado do stage + telemetria da política LLM (ADR-355)."""
    detail = {
        "success": True,
        "llm_calls_allowed": ctx.llm_calls_allowed,
        "inbox_review": stats.get("inbox_review", 0),
        "llm_classified": stats.get("llm_classified", 0),
    }
    warning = _routing_warning(ctx, stats)
    if warning:
        detail["warning"] = warning
    return detail


def _routing_warning(ctx: WorkspaceContext, stats: dict) -> Optional[str]:
    """Run determinístico que deixa documento no inbox analisa corpus menor — diz por quê."""
    inbox_review = stats.get("inbox_review", 0)
    if not ctx.llm_calls_allowed and inbox_review > 0:
        return (
            f"{inbox_review} documento(s) sem classificação determinística ficaram no "
            "inbox: run sem LLM não consulta o fallback de classificação, então o corpus "
            "analisado é menor que o de um run completo (ADR-355)."
        )
    if stats.get("unidentified", 0) > 0:
        return "1 ou mais documentos não identificados permanecerão no inbox para revisão manual."
    return None
