"""Stage wrapper for E5 Analysis — **Caminho B** (ADR-097, Sessão A5d).

Não usa mais ``MaterializationBridge`` nem o script legado ``main(root_dir)``.
Chama ``scripts.e5_analyze.main_with_store(ctx)`` que opera direto sobre
``ctx.get_artifact_store()``.

``main(root_dir)`` legado continua existindo para CLI direto e testes
legados, mas não é mais o caminho do pipeline web.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pipeline.context import WorkspaceContext


def run(ctx: "WorkspaceContext") -> dict:
    from scripts.e5_analyze import main_with_store

    return main_with_store(ctx)
