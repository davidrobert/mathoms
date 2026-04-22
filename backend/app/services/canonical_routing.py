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


def _compute_canonical_dest_path(
    source_path: Path,
    tenant_root: Path,
    project_root: Path,
    *,
    dest_group: str,
    e0_doc_type: str,
    institution: str | None,
    period: str | None,
    classification_meta: dict[str, Any] | None,
    content_hash: str | None,
) -> tuple[Path, Path, str] | None:
    """Inicializa config E0 + computa `(dest_directory, dest_path, src_hash)`.

    Retorna None se inputs inválidos (arquivo ausente, dest_group/type vazios).
    """
    from scripts.e0_route import (
        _init_config as route_init_config,
    )
    from scripts.e0_route import (
        build_final_name,
        dest_dir_for_group,
        file_hash,
    )

    if not source_path.exists() or not dest_group or not e0_doc_type:
        return None

    route_init_config(project_root)
    ext = _correct_extension(source_path)  # fixes wrong ext (PDF saved as .csv)
    classification = build_classification_for_final_name(
        dest_group=dest_group,
        e0_doc_type=e0_doc_type,
        institution=institution,
        period=period,
        classification_meta=classification_meta,
    )
    src_hash = content_hash or file_hash(source_path)
    final_name = build_final_name(classification, ext, content_hash=src_hash)
    dest_directory = dest_dir_for_group(tenant_root, dest_group)
    return dest_directory, dest_directory / final_name, src_hash


def _rel_path_str(path: Path, tenant_root_resolved: Path) -> str:
    """Caminho relativo POSIX; cai para o absoluto se fora do tenant_root."""
    try:
        rel = path.relative_to(tenant_root_resolved)
    except ValueError:
        rel = path
    return str(rel).replace("\\", "/")


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
    content_hash: str | None = None,
) -> tuple[Path, str] | None:
    """Rename/move a file (already in ``data/``) to its new canonical name.

    Used after reclassification: if ``doc_type``, ``institution`` or ``period``
    changed, the file must be moved so the stored path stays consistent with the
    classification stored in the DB.

    Differences from ``route_inbox_to_canonical_data``:
    - Source can be anywhere under ``tenant_root`` (not just ``inbox/``)
    - If the canonical name is unchanged the file is left in place and the
      existing path is returned as-is (no-op).

    The ``content_hash`` (sha256 hexdigest) is prepended as ``{hash[:12]}_`` to
    the canonical filename (ADR-084). When not provided it is computed from the
    file on disk.

    Returns ``(absolute_path, path_relative_to_tenant)`` or ``None`` on error.
    """
    from scripts.e0_route import resolve_collision

    computed = _compute_canonical_dest_path(
        current_path,
        tenant_root,
        project_root,
        dest_group=dest_group,
        e0_doc_type=e0_doc_type,
        institution=institution,
        period=period,
        classification_meta=classification_meta,
        content_hash=content_hash,
    )
    if computed is None:
        return None
    dest_directory, dest_path, src_hash = computed
    tenant_root_resolved = tenant_root.resolve()

    if current_path.resolve() == dest_path.resolve():
        # No-op: file já está no path canônico
        return current_path, _rel_path_str(current_path.resolve(), tenant_root_resolved)

    resolved = resolve_collision(dest_path, src_hash)
    if resolved is None:
        # dest já tem mesmo conteúdo (dupe exato) — remove src
        current_path.unlink(missing_ok=True)
        abs_final = dest_path
    else:
        dest_directory.mkdir(parents=True, exist_ok=True)
        shutil.move(str(current_path), str(resolved))
        abs_final = resolved

    return abs_final, _rel_path_str(abs_final, tenant_root_resolved)


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
    content_hash: str | None = None,
) -> tuple[Path, str] | None:
    """Move file from inbox to ``data/{dest}/`` with E0 canonical name.

    The ``content_hash`` (sha256 hexdigest of the uploaded bytes) is prepended as
    ``{hash[:12]}_`` to the canonical filename (ADR-084 — content-addressed
    uploads). When not provided it is computed from the file on disk.

    Returns ``(absolute_path, path_relative_to_tenant)`` or ``None`` if inputs invalid.
    Mirrors collision handling from ``e0_route.route_file``.
    """
    from scripts.e0_route import resolve_collision

    computed = _compute_canonical_dest_path(
        inbox_path,
        tenant_root,
        project_root,
        dest_group=dest_group,
        e0_doc_type=e0_doc_type,
        institution=institution,
        period=period,
        classification_meta=classification_meta,
        content_hash=content_hash,
    )
    if computed is None:
        return None
    dest_directory, dest_path, src_hash = computed
    tenant_root_resolved = tenant_root.resolve()

    resolved = resolve_collision(dest_path, src_hash)
    if resolved is None:
        if not dest_path.exists():
            return None
        inbox_path.unlink(missing_ok=True)
        abs_final = dest_path
    else:
        dest_directory.mkdir(parents=True, exist_ok=True)
        shutil.move(str(inbox_path), str(resolved))
        abs_final = resolved

    return abs_final, _rel_path_str(abs_final, tenant_root_resolved)
