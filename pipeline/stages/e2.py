"""Stage wrapper for E2 Extraction."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pipeline.context import WorkspaceContext


def _normalize_stem_for_incremental(stem: str) -> str:
    """Align E2 disk stem with DB stored_path stem (strip ``-0_original`` segment)."""
    if "-0_original" in stem:
        return stem.split("-0_original")[0]
    return stem


def _incremental_stems(ctx: WorkspaceContext) -> set[str] | None:
    """Return set of filename stems for incremental filtering, or None if not incremental."""
    if not ctx.incremental or not ctx.incremental_doc_paths:
        return None
    stems = set()
    for p in ctx.incremental_doc_paths:
        # stored_path is relative (e.g. "data/financial_statements/banco_extrato-0_original.pdf")
        stem = Path(p).stem
        stems.add(_normalize_stem_for_incremental(stem))
    return stems


def _matches_incremental(filepath: Path, allowed_stems: set[str]) -> bool:
    """True iff normalized disk stem equals one of the allowed normalized stems."""
    stem = _normalize_stem_for_incremental(filepath.stem)
    return stem in allowed_stems


def run(ctx: WorkspaceContext, extratos_only: bool = False, faturas_only: bool = False) -> dict:
    """Executa E2 extraction com contexto injetado."""
    from scripts.e2.common import _init_config as _e2_init
    _e2_init(ctx.root)

    from scripts.e2_extract import find_all_files, process_file, save_result

    files = find_all_files(extratos_only=extratos_only, faturas_only=faturas_only)

    # Incremental: filter to only new documents
    allowed = _incremental_stems(ctx)
    skipped = 0
    if allowed is not None:
        all_files = files
        files = [f for f in all_files if _matches_incremental(f, allowed)]
        skipped = len(all_files) - len(files)

    results = []
    for f in files:
        result = process_file(f)
        if result and not result.get("requires_llm_fallback"):
            out = save_result(result, f.name, ctx.e2_dir)
            results.append(out.name)

    detail: dict = {"success": True, "files_created": results, "total": len(results)}
    if allowed is not None:
        detail["incremental"] = True
        detail["skipped_existing"] = skipped
    return detail
