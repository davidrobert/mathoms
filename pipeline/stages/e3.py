"""Stage wrapper for E3 Reconciliation — **Caminho B** (ADR-097, Sessão A2).

Esta versão **não** usa ``MaterializationBridge`` nem o script legado
``main(root_dir)``. Chama ``scripts.e3_reconcile.main_with_store(ctx)`` que
opera direto sobre ``ctx.get_artifact_store()`` (Disk em CLI, DB em Web).

O ``main(root_dir)`` legado continua existindo no script para compatibilidade
com testes existentes e CLI direto, mas não é mais o caminho do pipeline web.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pipeline.context import WorkspaceContext


def run(ctx: "WorkspaceContext") -> dict:
    from scripts.e3_reconcile import main_with_store

    return main_with_store(ctx)
