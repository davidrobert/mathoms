"""Stage wrapper for E2 Extraction."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pipeline.context import WorkspaceContext


def run(ctx: WorkspaceContext, extratos_only: bool = False, faturas_only: bool = False) -> dict:
    """Executa E2 extraction com contexto injetado."""
    from scripts.e2.common import _init_config as _e2_init
    _e2_init(ctx.root)

    from scripts.e2_extract import find_all_files, process_file, save_result

    files = find_all_files(extratos_only=extratos_only, faturas_only=faturas_only)
    results = []
    for f in files:
        result = process_file(f)
        if result and not result.get("requires_llm_fallback"):
            out = save_result(result, f.name, ctx.e2_dir)
            results.append(out.name)

    return {"success": True, "files_created": results, "total": len(results)}
