"""Stage wrapper for E2 Extraction (Fase 3.2 — Caminho B).

Agora escreve via ``ArtifactStore`` em vez de diretamente em
``ctx.e2_dir``. ``DiskArtifactStore`` traduz writes para o layout legado
``processed/E2_extracts/*-2_extract.json``, preservando backward compat.
"""

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


def _incremental_stems(ctx: "WorkspaceContext") -> set[str] | None:
    """Return set of filename stems for incremental filtering, or None if not incremental."""
    if not ctx.incremental or not ctx.incremental_doc_paths:
        return None
    stems = set()
    for p in ctx.incremental_doc_paths:
        stem = Path(p).stem
        stems.add(_normalize_stem_for_incremental(stem))
    return stems


def run(
    ctx: "WorkspaceContext",
    extratos_only: bool = False,
    faturas_only: bool = False,
) -> dict:
    """Executa E2 extraction com contexto injetado (Caminho B)."""
    from scripts.e2.common import _init_config as _e2_init
    _e2_init(ctx.root)

    from scripts.e2_extract import run_with_store

    store = ctx.get_artifact_store()

    # Determina target_stage pelo modo do wrapper (sempre conhecido aqui).
    if faturas_only:
        target_stage = "E2-faturas"
    elif extratos_only:
        target_stage = "E2-extratos"
    else:
        target_stage = None  # modo unificado (CLI) — stage decidido por arquivo

    stats = run_with_store(
        store=store,
        target_stage=target_stage,
        extratos_only=extratos_only,
        faturas_only=faturas_only,
        incremental_allowed_stems=_incremental_stems(ctx),
    )

    detail: dict = {
        "success": stats["erros_validacao"] == 0,
        "total": stats["processados"],
        "transacoes_total": stats["transacoes_total"],
        "llm_fallback": stats["llm_fallback"],
        "warnings": stats["warnings"],
    }
    if _incremental_stems(ctx) is not None:
        detail["incremental"] = True
    return detail
