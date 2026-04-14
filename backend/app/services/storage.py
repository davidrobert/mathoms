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

    def validate_file(self, filename: str, size_bytes: int) -> tuple[bool, str]:
        """Validate file extension and size. Returns (ok, error_message)."""
        ext = Path(filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            return False, f"Tipo de arquivo não permitido: {ext}. Aceitos: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        if size_bytes > max_bytes:
            return False, f"Arquivo excede limite de {settings.MAX_UPLOAD_SIZE_MB}MB"
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
