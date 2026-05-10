"""drop stage_reviews.reviewer_notes (dead column).

Revision ID: c5d6e7f8a9b0
Revises: a4b5c6d7e8f9, b1a2c3d4e5f7
Create Date: 2026-05-09

A coluna `stage_reviews.reviewer_notes` (Phase 4 schema inicial) era
gravada pela UI de revisão (textarea "Notas do revisor") mas nunca foi
renderizada de volta — o usuário escrevia e nunca mais via. Removido o
textarea no frontend, o campo no DTO de request/response e a atribuição
no use case `action_review`. Este migration dropa a coluna fechando o
ciclo de cleanup.

Também merge dos dois heads paralelos (`a4b5c6d7e8f9` risk aggregate
A10.4 e `b1a2c3d4e5f7` business profile JSON A10.7).
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c5d6e7f8a9b0"
down_revision: Union[str, Sequence[str], None] = ("a4b5c6d7e8f9", "b1a2c3d4e5f7")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _stage_reviews_pre_drop() -> sa.Table:
    """Snapshot estático ANTES do drop, p/ offline SQL (`alembic upgrade --sql`).

    SQLite não suporta DROP COLUMN nativo: `batch_alter_table` recria a tabela
    e precisa do schema completo quando offline.
    """
    return sa.Table(
        "stage_reviews",
        sa.MetaData(),
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("pipeline_run_id", sa.String(36), nullable=False),
        sa.Column("stage", sa.String(50), nullable=False),
        sa.Column(
            "status",
            sa.Enum("pending", "approved", "edited", name="stagereviewstatus"),
            nullable=False,
        ),
        sa.Column("original_output_json", sa.JSON(), nullable=True),
        sa.Column("edited_output_json", sa.JSON(), nullable=True),
        sa.Column("validation_errors", sa.Text(), nullable=True),
        sa.Column("validation_issues", sa.JSON(), nullable=True),
        sa.Column("reviewer_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["pipeline_run_id"], ["pipeline_runs.id"], ondelete="CASCADE"),
    )


def _stage_reviews_post_drop() -> sa.Table:
    return sa.Table(
        "stage_reviews",
        sa.MetaData(),
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("pipeline_run_id", sa.String(36), nullable=False),
        sa.Column("stage", sa.String(50), nullable=False),
        sa.Column(
            "status",
            sa.Enum("pending", "approved", "edited", name="stagereviewstatus"),
            nullable=False,
        ),
        sa.Column("original_output_json", sa.JSON(), nullable=True),
        sa.Column("edited_output_json", sa.JSON(), nullable=True),
        sa.Column("validation_errors", sa.Text(), nullable=True),
        sa.Column("validation_issues", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["pipeline_run_id"], ["pipeline_runs.id"], ondelete="CASCADE"),
    )


def upgrade() -> None:
    with op.batch_alter_table("stage_reviews", copy_from=_stage_reviews_pre_drop()) as batch_op:
        batch_op.drop_column("reviewer_notes")


def downgrade() -> None:
    # Downgrade só restaura schema, não o dado (cleanup de coluna morta).
    with op.batch_alter_table("stage_reviews", copy_from=_stage_reviews_post_drop()) as batch_op:
        batch_op.add_column(sa.Column("reviewer_notes", sa.Text(), nullable=True))
