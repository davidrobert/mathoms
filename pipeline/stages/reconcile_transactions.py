"""Stage wrapper for E3 Reconciliation (ADR-097).

Chama ``scripts.reconcile_transactions.main_with_store(ctx)`` que opera direto sobre
``ctx.get_artifact_store()`` (Disk em CLI, DB em Web).

Piloto do logging estruturado (ADR-273): agregado final como INFO +
warnings por classe com contador (nunca por instância).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pipeline.observability import get_logger

if TYPE_CHECKING:
    from pipeline.context import WorkspaceContext

_WARNING_CLASSES = (
    "saldo_warnings",
    "temporal_warnings",
    "baseline_warnings",
    "period_warnings",
    "anachronic_warnings",
)


def run(ctx: "WorkspaceContext") -> dict:
    from scripts.reconcile_transactions import main_with_store

    result = main_with_store(ctx)
    _log_structured_aggregate(result)
    return result


def _log_structured_aggregate(result: dict) -> None:
    logger = get_logger("stages.reconcile_transactions")
    logger.info(
        "stage aggregate",
        extra={
            "event": "stage_aggregate",
            "statements_loaded": result.get("statements_loaded", 0),
            "statements_reconciled": result.get("statements_reconciled", 0),
            "artifacts_written": result.get("total", 0),
            "skipped_inputs": result.get("skipped_inputs", 0),
            # ADR-310 — sinal observável: faturas fora da cadeia de saldo.
            "saldo_exclusions": len(result.get("saldo_exclusions") or []),
        },
    )
    _log_warning_classes(logger, result)


def _log_warning_classes(logger, result: dict) -> None:
    for warning_class in _WARNING_CLASSES:
        count = len(result.get(warning_class) or [])
        if count:
            logger.warning(
                "warning class",
                extra={"event": "class_warning", "warning_class": warning_class, "count": count},
            )
