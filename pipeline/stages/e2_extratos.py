"""Stage wrapper para E2-extratos (bank statements).

Fase 1.5.3: wrappers separados de ``E2-extratos`` e ``E2-faturas`` — antes
ambos mapeavam para ``e2.run(ctx)`` sem flags, processando tudo nos dois.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pipeline.context import WorkspaceContext


def run(ctx: "WorkspaceContext") -> dict:
    """E2 executado apenas para extratos bancários."""
    from pipeline.stages.e2 import run as _run

    return _run(ctx, extratos_only=True)
