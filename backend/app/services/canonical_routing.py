"""Canonical E0-style filenames for web uploads — aligns with ``scripts/e0_route.build_final_name``."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any


def ensure_minus_zero_original_filename(filename: str) -> str:
    """Append ``-0_original`` before extension when missing (JSON / generic copies)."""
    p = Path(filename)
    stem, suf = p.stem, p.suffix
    if "-0_original" in stem:
        return filename
    return f"{stem}-0_original{suf}"


def build_classification_for_final_name(
    *,
    dest_group: str,
    e0_doc_type: str,
    institution: str | None,
    period: str | None,
    classification_meta: dict[str, Any] | None,
) -> dict[str, Any]:
    """Build the dict expected by ``e0_route.build_final_name``."""
    meta = classification_meta or {}
    c: dict[str, Any] = {
        "dest_group": dest_group,
        "doc_type": e0_doc_type,
        "institution": institution or "unknown",
        "period": period,
    }
    llm = meta.get("llm")
    if isinstance(llm, dict):
        if llm.get("final_name"):
            c["source"] = "llm"
            c["final_name"] = llm["final_name"]
        if llm.get("member"):
            c["member"] = llm["member"]
    return c


def route_inbox_to_canonical_data(
    inbox_path: Path,
    tenant_root: Path,
    project_root: Path,
    *,
    dest_group: str,
    e0_doc_type: str,
    institution: str | None,
    period: str | None,
    classification_meta: dict[str, Any] | None,
) -> tuple[Path, str] | None:
    """Move file from inbox to ``data/{dest}/`` with E0 canonical name.

    Returns ``(absolute_path, path_relative_to_tenant)`` or ``None`` if inputs invalid.
    Mirrors collision handling from ``e0_route.route_file``.
    """
    from scripts.e0_route import (
        _init_config as route_init_config,
        build_final_name,
        dest_dir_for_group,
        file_hash,
        resolve_collision,
    )

    if not inbox_path.exists() or not dest_group or not e0_doc_type:
        return None

    route_init_config(project_root)
    ext = inbox_path.suffix.lower()
    classification = build_classification_for_final_name(
        dest_group=dest_group,
        e0_doc_type=e0_doc_type,
        institution=institution,
        period=period,
        classification_meta=classification_meta,
    )
    final_name = build_final_name(classification, ext)
    dest_directory = dest_dir_for_group(tenant_root, dest_group)
    dest_path = dest_directory / final_name
    src_hash = file_hash(inbox_path)

    resolved = resolve_collision(dest_path, src_hash)
    tenant_root = tenant_root.resolve()

    if resolved is None:
        if not dest_path.exists():
            return None
        inbox_path.unlink(missing_ok=True)
        abs_final = dest_path
    else:
        dest_path = resolved
        dest_directory.mkdir(parents=True, exist_ok=True)
        shutil.move(str(inbox_path), str(dest_path))
        abs_final = dest_path

    try:
        rel = abs_final.relative_to(tenant_root)
    except ValueError:
        rel = abs_final
    rel_str = str(rel).replace("\\", "/")
    return abs_final, rel_str
