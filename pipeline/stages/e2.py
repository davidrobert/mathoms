"""Stage wrapper for E2 Extraction."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pipeline.context import WorkspaceContext


def _incremental_stems(ctx: WorkspaceContext) -> set[str] | None:
    """Return set of filename stems for incremental filtering, or None if not incremental."""
    if not ctx.incremental or not ctx.incremental_doc_paths:
        return None
    stems = set()
    for p in ctx.incremental_doc_paths:
        # stored_path is relative (e.g. "data/financial_statements/banco_extrato.pdf")
        stem = Path(p).stem
        # Also handle routed names (e.g. "itau_extratoconta_202601-0_original.csv")
        # Strip the -0_original suffix to match against the base name
        if "-0_original" in stem:
            stem = stem.split("-0_original")[0]
        stems.add(stem)
    return stems


def _matches_incremental(filepath: Path, allowed_stems: set[str]) -> bool:
    """Check if a file matches the incremental document set."""
    stem = filepath.stem
    # Check direct match
    if stem in allowed_stems:
        return True
    # Check if any allowed stem is a prefix (routed files may have suffixes)
    for s in allowed_stems:
        if stem.startswith(s) or s.startswith(stem):
            return True
    return False


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
