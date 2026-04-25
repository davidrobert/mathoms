"""Stage wrapper for E5 Analysis (ADR-097).

Chama ``scripts.e5_analyze.main_with_store(ctx)`` que opera direto sobre
``ctx.get_artifact_store()``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pipeline.context import WorkspaceContext


def run(ctx: "WorkspaceContext") -> dict:
    from scripts.e5_analyze import main_with_store

    return main_with_store(ctx)
