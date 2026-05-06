"""Helpers de modo incremental para stages globais E1 (ADR-080 + ADR-159)."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Iterable

if TYPE_CHECKING:
    from pipeline.context import WorkspaceContext


def normalize_stem(p: str | Path) -> str:
    """Stem canônico para matching incremental — strip de ``-0_original``."""
    stem = Path(p).stem
    if "-0_original" in stem:
        stem = stem.split("-0_original")[0]
    return stem


def allowed_stems(ctx: "WorkspaceContext") -> set[str] | None:
    """Conjunto de stems do allowlist incremental, ou ``None`` se modo full."""
    if not ctx.incremental or not ctx.incremental_doc_paths:
        return None
    return {normalize_stem(p) for p in ctx.incremental_doc_paths}


def filter_to_incremental(ctx: "WorkspaceContext", candidates: Iterable[Path]) -> list[Path]:
    """Filtra ``candidates`` ao allowlist. Modo full devolve a lista intacta."""
    stems = allowed_stems(ctx)
    if stems is None:
        return list(candidates)
    return [c for c in candidates if normalize_stem(c) in stems]


def has_incremental_overlap(ctx: "WorkspaceContext", candidates: Iterable[Path]) -> bool:
    """Modo full → ``True``. Modo incremental → True se algum candidate casa."""
    stems = allowed_stems(ctx)
    if stems is None:
        return True
    return any(normalize_stem(c) in stems for c in candidates)
