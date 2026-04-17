"""StorageService — per-tenant file storage with security controls."""

import os
import re
import shutil
from pathlib import Path
from typing import Optional

from backend.app.core.config import settings

ALLOWED_EXTENSIONS = {
    ".pdf", ".xlsx", ".xls", ".csv",
    ".jpg", ".jpeg", ".png",
    ".json",
}

# Magic number (file signature) prefixes for supported types (P1.3).
# Maps extension → list of valid byte-prefixes (OR-composed). CSV/JSON are
# plain text — they have no reliable signature, validated by extension only.
# References:
#   PDF: ISO 32000-1 §7.5.2 ("%PDF-")
#   ZIP-based (xlsx/docx): PKWARE APPNOTE ("PK\x03\x04" / "PK\x05\x06" /
#     "PK\x07\x08")
#   OLE Compound Document (xls legacy): ".\\xd0\\xcf\\x11\\xe0\\xa1\\xb1\\x1a\\xe1"
#   JPEG: ISO/IEC 10918-1 ("\\xff\\xd8\\xff")
#   PNG: RFC 2083 ("\\x89PNG\\r\\n\\x1a\\n")
_MAGIC_SIGNATURES: "dict[str, tuple[bytes, ...]]" = {
    ".pdf":  (b"%PDF-",),
    ".xlsx": (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08"),
    ".xls":  (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1", b"PK\x03\x04"),  # OLE2 or ZIP (xlsx renamed)
    ".jpg":  (b"\xff\xd8\xff",),
    ".jpeg": (b"\xff\xd8\xff",),
    ".png":  (b"\x89PNG\r\n\x1a\n",),
}


def detect_actual_mime(content: bytes) -> str | None:
    """Detect real MIME type from the first bytes of file content.

    Useful when the file extension or HTTP Content-Type header is unreliable
    (e.g. a PDF exported with a .csv extension).  Returns None when the type
    cannot be determined from the header bytes alone (e.g. plain-text CSV/JSON).
    """
    if not content:
        return None
    if content[:5] == b"%PDF-":
        return "application/pdf"
    if content[:4] in (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08"):
        # Both .xlsx and .zip share the PK signature; treat as spreadsheet
        # (upload pipeline will re-classify if it's some other ZIP-based format).
        return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    if content[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
        return "application/vnd.ms-excel"
    if content[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if content[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    return None


def _validate_magic_number(filename: str, content: bytes) -> tuple[bool, str]:
    """Verify content prefix matches expected magic bytes for its extension.

    Returns (ok, reason). Unknown extensions (csv/json) always pass since
    they have no reliable magic. Content shorter than the smallest known
    signature is rejected as "malformed".
    """
    ext = Path(filename).suffix.lower()
    expected = _MAGIC_SIGNATURES.get(ext)
    if expected is None:
        return True, ""
    if not content:
        return False, "Arquivo vazio"
    for sig in expected:
        if content.startswith(sig):
            return True, ""
    # Hex preview of first few bytes to aid debugging without leaking content
    preview = content[:8].hex()
    return False, (
        f"Conteúdo não corresponde à extensão {ext} "
        f"(bytes iniciais: {preview})"
    )

TENANT_SUBDIRS = [
    "inbox",
    "data/financial_statements",
    "data/income_tax_br",
    "data/income_tax_us",
    "data/real_estate",
    "data/vehicles",
    "processed/E2_extracts",
    "processed/E3_reconciled",
    "processed/E4_unified",
    "processed/E5_analysis",
    "processed/E7_review",
    "output",
    "members",
    "logs",
]


def _safe_filename(name: str) -> str:
    """Sanitize filename: keep alphanumeric, dots, hyphens, underscores."""
    name = os.path.basename(name)
    name = re.sub(r'[^\w\-.]', '_', name)
    name = re.sub(r'__+', '_', name)
    if name.startswith('.'):
        name = '_' + name
    return name[:255]


class StorageService:
    """Manages per-tenant file storage on the local filesystem."""

    def __init__(self, storage_root: Optional[Path] = None):
        self.storage_root = Path(storage_root or settings.STORAGE_ROOT).resolve()

    def tenant_root(self, workspace_id: str) -> Path:
        return self.storage_root / workspace_id

    def ensure_tenant_dirs(self, workspace_id: str) -> Path:
        """Create the full tenant directory tree. Returns the tenant root."""
        root = self.tenant_root(workspace_id)
        for subdir in TENANT_SUBDIRS:
            (root / subdir).mkdir(parents=True, exist_ok=True)
        return root

    def validate_file(
        self,
        filename: str,
        size_bytes: int,
        content: Optional[bytes] = None,
    ) -> tuple[bool, str]:
        """Validate file extension, size, and (optionally) magic number.

        Args:
            filename: client-provided filename.
            size_bytes: total size of the upload.
            content: if provided, magic-number verification is performed (P1.3).
                Falsy or None disables magic-check for backward compatibility
                (legacy callers that only know size).

        Returns ``(ok, error_message)``.
        """
        ext = Path(filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            return False, f"Tipo de arquivo não permitido: {ext}. Aceitos: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        if size_bytes > max_bytes:
            return False, f"Arquivo excede limite de {settings.MAX_UPLOAD_SIZE_MB}MB"
        if content is not None:
            ok, err = _validate_magic_number(filename, content)
            if not ok:
                return False, err
        return True, ""

    def check_workspace_quota(self, workspace_id: str) -> tuple[bool, int]:
        """Check if workspace is within storage quota. Returns (within_quota, current_bytes)."""
        root = self.tenant_root(workspace_id)
        if not root.exists():
            return True, 0
        total = sum(f.stat().st_size for f in root.rglob("*") if f.is_file())
        max_bytes = settings.MAX_STORAGE_PER_WORKSPACE_MB * 1024 * 1024
        return total < max_bytes, total

    def save_to_inbox(self, workspace_id: str, filename: str, content: bytes) -> Path:
        """Save uploaded file to tenant inbox. Returns the stored path."""
        self.ensure_tenant_dirs(workspace_id)
        safe_name = _safe_filename(filename)
        dest = self.tenant_root(workspace_id) / "inbox" / safe_name

        counter = 1
        while dest.exists():
            stem = Path(safe_name).stem
            ext = Path(safe_name).suffix
            dest = self.tenant_root(workspace_id) / "inbox" / f"{stem}_{counter}{ext}"
            counter += 1

        dest.write_bytes(content)
        return dest

    def move_to_data(self, workspace_id: str, inbox_path: Path, data_subdir: str, new_name: str) -> Path:
        """Move file from inbox to the correct data/ subdirectory after classification."""
        dest_dir = self.tenant_root(workspace_id) / "data" / data_subdir
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / _safe_filename(new_name)
        shutil.move(str(inbox_path), str(dest))
        return dest

    def resolve_path(self, workspace_id: str, relative_path: str) -> Optional[Path]:
        """Safely resolve a relative path within the tenant root. Returns None on traversal."""
        tenant = self.tenant_root(workspace_id)
        resolved = (tenant / relative_path).resolve()
        if not str(resolved).startswith(str(tenant)):
            return None
        return resolved

    def abs_stored_file(self, workspace_id: str, stored_path: str | None) -> Optional[Path]:
        """Resolve ``stored_path`` to an absolute ``Path`` (legacy absolute or tenant-relative)."""
        if not stored_path:
            return None
        p = Path(stored_path)
        if p.is_absolute():
            return p if p.exists() else None
        return self.resolve_path(workspace_id, stored_path)

    def delete_file(self, workspace_id: str, relative_path: str) -> bool:
        """Delete a file within the tenant storage. Returns True if deleted."""
        resolved = self.resolve_path(workspace_id, relative_path)
        if resolved is None or not resolved.is_file():
            return False
        resolved.unlink()
        return True

    def list_files(self, workspace_id: str, subdir: str = "") -> list[dict]:
        """List files in a tenant subdirectory."""
        root = self.tenant_root(workspace_id) / subdir if subdir else self.tenant_root(workspace_id)
        if not root.exists():
            return []
        return [
            {
                "name": f.name,
                "path": str(f.relative_to(self.tenant_root(workspace_id))),
                "size_bytes": f.stat().st_size,
            }
            for f in sorted(root.rglob("*"))
            if f.is_file()
        ]

    def delete_tenant(self, workspace_id: str) -> bool:
        """Remove all storage for a tenant. Returns True if removed."""
        root = self.tenant_root(workspace_id)
        if root.exists():
            shutil.rmtree(root)
            return True
        return False
