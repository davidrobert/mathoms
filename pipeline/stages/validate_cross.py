"""Stage wrapper for cross-validation (E7-crossval).

Roda 14 checks determinísticos CV1-CV14 sobre o output de ``analyze_finances``
(E5). Chama ``scripts.e7_review.main_with_store(ctx, mode="crossval")``.

Nota: ``scripts/e7_review.py`` ficou com nome legado por compat após a remoção
de ``review_finances`` (superseded por ADR-199); a parte que sobrou é
exclusivamente crossval.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pipeline.context import WorkspaceContext


def run(ctx: "WorkspaceContext") -> dict:
    from scripts.e7_review import main_with_store

    result = main_with_store(ctx, mode="crossval")
    result["stage"] = "validate_cross"
    return result
