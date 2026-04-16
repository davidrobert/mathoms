"""documents_pipeline_touch — last pipeline run + E2 extract flag

Revision ID: g2a3b4c5d6e7
Revises: f1a2b3c4d5e6
Create Date: 2026-04-16
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "g2a3b4c5d6e7"
# Merge: content_first (f1…) e bank_accounts label (e6…) divergiram — une os dois heads.
down_revision: Union[str, Sequence[str], None] = ("f1a2b3c4d5e6", "e6f7a8b9c0d1")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column(
            "pipeline_last_run_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "documents",
        sa.Column(
            "pipeline_e2_extract_ok",
            sa.Boolean(),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("documents", "pipeline_e2_extract_ok")
    op.drop_column("documents", "pipeline_last_run_at")
