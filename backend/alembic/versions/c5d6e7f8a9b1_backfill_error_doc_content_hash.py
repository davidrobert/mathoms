"""Backfill content_hash em documentos status='error' com stored_path acessível.

Hot-fix da regressão de dedupe descrita em ``CLAUDE.md §Dedupe de uploads``:
``_record_validation_failure`` historicamente persistia ``Document`` com
``content_hash=NULL``, e o partial unique index
``ux_documents_workspace_content_hash WHERE content_hash IS NOT NULL`` não
bloqueava re-upload das mesmas bytes. O fix de código (`document_upload_service`)
preenche o hash em uploads novos; esta migration cobre rows legadas.

Comportamento:
- Para cada row em ``documents`` com ``status='error'``,
  ``content_hash IS NULL`` e ``stored_path IS NOT NULL``: lê o arquivo,
  computa SHA-256 e atualiza ``content_hash``.
- Se o arquivo não existir mais em disco, mantém ``content_hash=NULL``
  (zombie row continua, mas não bloqueia a constraint).
- Se a hash colidir com outra row do mesmo workspace, mantém ``NULL`` —
  evita ``IntegrityError`` que abortaria a migration.

Em instalações típicas a query SELECT inicial retorna **0 rows** (validation
failures historicamente não tinham ``stored_path``), o que torna a migration
um no-op idempotente e seguro de re-rodar.

Revision ID: c5d6e7f8a9b1
Revises: b1a2c3d4e5f7
Create Date: 2026-05-09
"""

from __future__ import annotations

import hashlib
import logging
import os
from pathlib import Path
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import context, op

revision: str = "c5d6e7f8a9b1"
down_revision: Union[str, None] = "b1a2c3d4e5f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

logger = logging.getLogger("alembic.runtime.migration")


def _resolve_path(stored_path: str, workspace_id: str, storage_root: Path) -> Path:
    p = Path(stored_path)
    if p.is_absolute():
        return p
    return storage_root / workspace_id / stored_path


def _storage_root() -> Path:
    raw = os.environ.get("MATHOMS_STORAGE_ROOT")
    if raw:
        return Path(raw).resolve()
    return Path.cwd() / "storage"


def upgrade() -> None:
    if context.is_offline_mode():
        # Backfill data-only — depende de SELECT/UPDATE com round-trip ao DB
        # e leitura de filesystem. Modo --sql (offline) não suporta nada disso.
        # Skip silencioso preserva preview pra revisão de DBA.
        return

    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            "SELECT id, workspace_id, stored_path FROM documents "
            "WHERE status = 'error' "
            "AND content_hash IS NULL "
            "AND stored_path IS NOT NULL"
        )
    ).fetchall()

    if not rows:
        logger.info("backfill_error_doc_content_hash: 0 rows to process")
        return

    storage_root = _storage_root()
    updated = skipped_missing = skipped_collision = 0

    for doc_id, workspace_id, stored_path in rows:
        path = _resolve_path(stored_path, workspace_id, storage_root)
        try:
            data = path.read_bytes()
        except (FileNotFoundError, OSError):
            skipped_missing += 1
            continue

        content_hash = hashlib.sha256(data).hexdigest()
        collision = bind.execute(
            sa.text(
                "SELECT 1 FROM documents "
                "WHERE workspace_id = :ws AND content_hash = :h AND id != :id "
                "LIMIT 1"
            ),
            {"ws": workspace_id, "h": content_hash, "id": doc_id},
        ).fetchone()
        if collision:
            skipped_collision += 1
            continue

        bind.execute(
            sa.text(
                "UPDATE documents SET content_hash = :h WHERE id = :id AND content_hash IS NULL"
            ),
            {"h": content_hash, "id": doc_id},
        )
        updated += 1

    logger.info(
        "backfill_error_doc_content_hash: updated=%d skipped_missing=%d skipped_collision=%d",
        updated,
        skipped_missing,
        skipped_collision,
    )


def downgrade() -> None:
    # Hashes são determinísticos a partir do conteúdo; re-rodar upgrade
    # reconstrói o mesmo estado. Não há downgrade seguro — não conseguimos
    # distinguir um content_hash backfillado de um genuíno.
    pass
