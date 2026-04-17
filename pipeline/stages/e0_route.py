"""Stage wrapper for E0 Route (inbox routing)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pipeline.context import WorkspaceContext


def run(ctx: WorkspaceContext) -> dict:
    """Executa E0 route com contexto injetado.

    Exit codes do e0_route.py:
      0 — tudo roteado com sucesso
      1 — erro crítico (falha real)
      2 — partial success: houve documentos não identificados, mas sem erro.
           Tratamos como sucesso com aviso para não interromper o pipeline.
    """
    from scripts.e0_route import main as e0_route_main

    try:
        e0_route_main(root_dir=ctx.root)
    except SystemExit as exc:
        code = exc.code if exc.code is not None else 0
        if code == 2:
            # Partial success: documentos não identificados ficam em inbox para revisão.
            # Não interrompe o pipeline — documentos roteados prosseguem normalmente.
            return {"success": True, "warning": "1 ou mais documentos não identificados permanecerão no inbox para revisão manual."}
        # code == 1 ou outro: erro real — re-lança para o orquestrador tratar como falha
        raise

    return {"success": True}
