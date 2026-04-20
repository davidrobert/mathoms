"""Stage wrapper for E5.N Narrativas — **Caminho B** (ADR-097, Sessão A5e).

Chama ``scripts.e5n_narrativas.main_with_store(ctx)`` direto, sem
``MaterializationBridge``. ``main(root_dir)`` legado continua existindo
para CLI direto.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pipeline.context import WorkspaceContext


def run(ctx: "WorkspaceContext") -> dict:
    from scripts.e5n_narrativas import main_with_store

    return main_with_store(ctx)
