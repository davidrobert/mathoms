"""Re-link de ``stored_path`` stale via ``content_hash`` (A37.l3 · ADR-329).

O E0-route move arquivos de ``inbox/`` para ``inbox_processed/<data>/`` sem
atualizar ``documents.stored_path`` — retry e bulk reclassify devolviam
``no_file``/skip para sempre. O match de relocação é EXCLUSIVAMENTE por
SHA-256 do conteúdo (``documents.content_hash``): relocar por basename
re-linkaria o doc a conteúdo alheio em colisão de nome.
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

from backend.app.models.document import Document

logger = logging.getLogger("mathoms.documents.stored_path_selfheal")

_SEARCH_SUBDIR = "inbox_processed"
_HASH_CHUNK_BYTES = 1024 * 1024


def _sha256_of_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(_HASH_CHUNK_BYTES), b""):
            digest.update(chunk)
    return digest.hexdigest()


class StoredPathSelfHealer:
    """Índice lazy ``content_hash → path`` de ``inbox_processed/**`` de um tenant."""

    def __init__(self, tenant_root: Path) -> None:
        self._tenant_root = Path(tenant_root)
        self._index: dict[str, Path] | None = None

    def _build_index(self) -> dict[str, Path]:
        search_root = self._tenant_root / _SEARCH_SUBDIR
        if not search_root.is_dir():
            return {}
        index: dict[str, Path] = {}
        for candidate in sorted(p for p in search_root.rglob("*") if p.is_file()):
            index.setdefault(_sha256_of_file(candidate), candidate)
        return index

    def relocate(self, doc: Document) -> Path | None:
        """Aponta ``doc.stored_path`` para o arquivo atual (match por hash); ``None`` se ausente."""
        if not doc.content_hash:
            return None
        if self._index is None:
            self._index = self._build_index()
        found = self._index.get(doc.content_hash)
        if found is None:
            return None
        doc.stored_path = found.relative_to(self._tenant_root).as_posix()
        logger.info("stored_path_selfheal doc=%s relocated_to=%s", doc.id, doc.stored_path)
        return found
