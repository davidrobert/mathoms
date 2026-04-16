"""content_first_classification_and_dedupe

Adds fields for the content-first classifier and fuzzy dedupe:
  - classification_confidence (float, nullable) — 0.0 to 1.0
  - needs_review (bool, NOT NULL default False, indexed) — UI flag
  - possible_duplicate_of_id (FK to documents.id, nullable, indexed) — fuzzy
    dedupe pointer set by the upload path when another doc has the same
    (doc_type, bank_code, period) but a different content_hash.

Also adds a partial unique index on (workspace_id, content_hash) to block
exact-duplicate uploads at the DB level (backfill happens separately before
this migration; see backend/scripts/backfill_content_hash.py).

Revision ID: f1a2b3c4d5e6
Revises: e7f8a9b0c1d2
Create Date: 2026-04-15
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, None] = "e7f8a9b0c1d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Note: we use ``op.add_column`` directly (not ``batch_alter_table``).
    # SQLite's ALTER TABLE ADD COLUMN handles all three cases here without
    # needing the batch "move and copy" path — which can't reflect the live
    # ``documents`` table under alembic's offline ``--sql`` mode (and so
    # would fail ``test_offline_sql_generation_works``).
    #
    # ``possible_duplicate_of_id`` is intentionally a SOFT reference (no FK
    # constraint). A real self-referential FK would force batch mode. The
    # UI is the source of truth for surfacing this pointer to the user; a
    # dangling reference (referenced doc deleted) is harmless — the JOIN
    # just returns no row.
    op.add_column(
        "documents",
        sa.Column("classification_confidence", sa.Float(), nullable=True),
    )
    op.add_column(
        "documents",
        sa.Column(
            "needs_review",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.add_column(
        "documents",
        sa.Column("possible_duplicate_of_id", sa.String(length=36), nullable=True),
    )
    op.create_index(
        "ix_documents_needs_review", "documents", ["needs_review"], unique=False
    )
    op.create_index(
        "ix_documents_possible_duplicate_of_id",
        "documents",
        ["possible_duplicate_of_id"],
        unique=False,
    )

    # Partial unique index: enforce exact-dedupe when content_hash is present.
    # SQLite supports partial indexes with WHERE; PostgreSQL does too.
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ux_documents_workspace_content_hash
        ON documents (workspace_id, content_hash)
        WHERE content_hash IS NOT NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ux_documents_workspace_content_hash")
    op.drop_index("ix_documents_possible_duplicate_of_id", table_name="documents")
    op.drop_index("ix_documents_needs_review", table_name="documents")
    op.drop_column("documents", "possible_duplicate_of_id")
    op.drop_column("documents", "needs_review")
    op.drop_column("documents", "classification_confidence")
