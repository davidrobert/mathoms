"""Stage wrapper for E4 Categorization (ADR-097).

Chama ``scripts.e4_categorize.main_with_store(ctx)`` que opera direto sobre
``ctx.get_artifact_store()`` (Disk em CLI, DB em Web).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pipeline.context import WorkspaceContext


def run(ctx: "WorkspaceContext") -> dict:
    from scripts.e4_categorize import main_with_store

    return main_with_store(ctx)
