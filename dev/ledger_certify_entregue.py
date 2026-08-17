"""Fail-closed do modo entregue da KR-B — predicados puros, sem I/O.

O modo entregue pontua a KR-B no E3 persistido de um run pinado. Workspace-latest
é proibido; run sem evidência de enforce no ``output_summary`` é recusado.
"""

from __future__ import annotations


class EntregueRecusado(ValueError):
    """Modo entregue recusou o run — não pontua KR-B."""


def _retention(summary: dict | None) -> dict:
    block = summary.get("collapse_retention") if isinstance(summary, dict) else None
    return block if isinstance(block, dict) else {}


def _require_cortadas(run_id: str, retention: dict) -> int:
    if not retention:
        raise EntregueRecusado(
            f"run {run_id} sem collapse_retention no output_summary — não prova enforce"
        )
    cortadas = int(retention.get("removals_publicadas") or 0)
    if cortadas <= 0:
        raise EntregueRecusado(
            f"run {run_id} sem rows cortadas (removals_publicadas={cortadas}) "
            "— sombra ou enforce sem corte"
        )
    return cortadas


def evidence_from_retention(
    run_id: str,
    summary: dict | None,
    executor_revision: str | None,
) -> dict:
    """Extrai evidência de enforce do ``output_summary`` do E3 daquele run."""
    retention = _retention(summary)
    return {
        "run_id": run_id,
        "executor_revision": executor_revision,
        "cortadas": _require_cortadas(run_id, retention),
        "retido_por_override": int(retention.get("retido_por_override") or 0),
    }


def require_pinned_run(run_id: str | None) -> str:
    if not run_id:
        raise EntregueRecusado("modo entregue exige --run <run_id> (workspace-latest é proibido)")
    return run_id
