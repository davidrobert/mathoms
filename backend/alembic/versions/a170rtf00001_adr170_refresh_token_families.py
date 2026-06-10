"""ADR-170 (W3-T03): refresh_token_families — tabela aditiva de sessões
efêmeras (regeneráveis por re-login; rollback = revert + downgrade -1),
só hashes sha256, secret independente de SECRET_KEY/Fernet.
Revision ID: a170rtf00001 · Revises: f2a3b4c5d6e7 · Create Date: 2026-06-09."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a170rtf00001"
down_revision: Union[str, Sequence[str], None] = "f2a3b4c5d6e7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "refresh_token_families",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(length=36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("token_version_at_issue", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("prev_token_hash", sa.String(length=64), nullable=True),
        sa.Column("prev_rotated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rotation_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_refresh_token_families_user_id", "refresh_token_families", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_refresh_token_families_user_id", table_name="refresh_token_families")
    op.drop_table("refresh_token_families")
