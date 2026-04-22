"""f8_feature_flags

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-04-15

ADR-074 §"Feature flag" — workspace-level boolean flags.

Uma linha por workspace com dict JSON `{flag: bool}`. Defaults em código
(`feature_flags_service.DEFAULTS`) — rows criadas sob demanda ao mudar
uma flag.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "feature_flags",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.String(length=36),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("flags_json", sa.JSON(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("workspace_id", name="uq_feature_flags_workspace"),
    )
    op.create_index("ix_feature_flags_workspace_id", "feature_flags", ["workspace_id"])


def downgrade() -> None:
    op.drop_index("ix_feature_flags_workspace_id", table_name="feature_flags")
    op.drop_table("feature_flags")
