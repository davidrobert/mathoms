"""Canonical E0-style filenames for web uploads — aligns with ``scripts/e0_route.build_final_name``."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

# Maps detected MIME → correct file extension.
# Used to fix files uploaded with a wrong extension (e.g. a PDF named .csv).
_MIME_TO_EXT: dict[str, str] = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "application/vnd.ms-excel": ".xls",
    "image/jpeg": ".jpg",
    "image/png": ".png",
}


def _correct_extension(path: Path) -> str:
    """Return the correct file extension based on magic bytes.

    If the file's declared extension doesn't match its actual content (e.g. a
    PDF saved as .csv), returns the true extension.  Falls back to the declared
    extension when the type is unknown (CSV, JSON, plain text, etc.).
    """
    from backend.app.services.storage import detect_actual_mime

    try:
        header = path.read_bytes()[:8]
    except OSError:
        return path.suffix.lower()

    actual_mime = detect_actual_mime(header)
    if actual_mime is None:
        return path.suffix.lower()

    correct = _MIME_TO_EXT.get(actual_mime)
    if correct is None:
        return path.suffix.lower()

    declared = path.suffix.lower()
    if declared != correct:
        return correct  # extension mismatch — use the real one
    return declared


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


def rename_to_canonical(
    current_path: Path,
    tenant_root: Path,
    project_root: Path,
    *,
    dest_group: str,
    e0_doc_type: str,
    institution: str | None,
    period: str | None,
    classification_meta: dict[str, Any] | None,
) -> tuple[Path, str] | None:
    """Rename/move a file (already in ``data/``) to its new canonical name.

    Used after reclassification: if ``doc_type``, ``institution`` or ``period``
    changed, the file must be moved so the stored path stays consistent with the
    classification stored in the DB.

    Differences from ``route_inbox_to_canonical_data``:
    - Source can be anywhere under ``tenant_root`` (not just ``inbox/``)
    - If the canonical name is unchanged the file is left in place and the
      existing path is returned as-is (no-op).

    Returns ``(absolute_path, path_relative_to_tenant)`` or ``None`` on error.
    """
    from scripts.e0_route import (
        _init_config as route_init_config,
        build_final_name,
        dest_dir_for_group,
        file_hash,
        resolve_collision,
    )

    if not current_path.exists() or not dest_group or not e0_doc_type:
        return None

    route_init_config(project_root)
    ext = _correct_extension(current_path)  # fixes wrong extension (e.g. PDF saved as .csv)
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

    tenant_root_resolved = tenant_root.resolve()

    # No-op: file is already at the right canonical path
    if current_path.resolve() == dest_path.resolve():
        try:
            rel = current_path.resolve().relative_to(tenant_root_resolved)
        except ValueError:
            rel = current_path
        return current_path, str(rel).replace("\\", "/")

    src_hash = file_hash(current_path)
    resolved = resolve_collision(dest_path, src_hash)

    if resolved is None:
        # dest_path already has the same content (exact duplicate) — remove src
        current_path.unlink(missing_ok=True)
        abs_final = dest_path
    else:
        dest_directory.mkdir(parents=True, exist_ok=True)
        shutil.move(str(current_path), str(resolved))
        abs_final = resolved

    try:
        rel = abs_final.relative_to(tenant_root_resolved)
    except ValueError:
        rel = abs_final
    return abs_final, str(rel).replace("\\", "/")


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
    ext = _correct_extension(inbox_path)  # fixes wrong extension (e.g. PDF saved as .csv)
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
