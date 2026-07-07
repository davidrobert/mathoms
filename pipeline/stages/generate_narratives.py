"""Stage wrapper for E5.N Narrativas (ADR-097).

Chama ``scripts.generate_narratives.main_with_store(ctx)`` direto.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pipeline.context import WorkspaceContext


def run(ctx: "WorkspaceContext") -> dict:
    from scripts.generate_narratives import main_with_store

    return main_with_store(ctx)
