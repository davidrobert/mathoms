"""adr-262 workspace_memory_confirmations append-only (Revision: adr262memconf, Revises: a17l5seed, Create Date: 2026-05-23). Tabela transversal de endosse para campos derivados (E5, IRPF metadata, Risk, family_members); 2 índices: ix_wmc_ws_key (lookup), ix_wmc_ws_confirmed_at (stale detection ≥12 meses)."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "adr262memconf"
down_revision: Union[str, None] = "a17l5seed"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _create_table() -> None:
    op.create_table(
        "workspace_memory_confirmations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("memory_key", sa.String(length=256), nullable=False),
        sa.Column("source_aggregate", sa.String(length=64), nullable=False),
        sa.Column("confirmed_value_snapshot", sa.Text(), nullable=True),
        sa.Column("confirmed_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["confirmed_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )


def _create_indexes() -> None:
    with op.batch_alter_table("workspace_memory_confirmations", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_workspace_memory_confirmations_workspace_id"),
            ["workspace_id"],
            unique=False,
        )
        batch_op.create_index("ix_wmc_ws_key", ["workspace_id", "memory_key"], unique=False)
        batch_op.create_index(
            "ix_wmc_ws_confirmed_at", ["workspace_id", "confirmed_at"], unique=False
        )


def upgrade() -> None:
    _create_table()
    _create_indexes()


def downgrade() -> None:
    with op.batch_alter_table("workspace_memory_confirmations", schema=None) as batch_op:
        batch_op.drop_index("ix_wmc_ws_confirmed_at")
        batch_op.drop_index("ix_wmc_ws_key")
        batch_op.drop_index(batch_op.f("ix_workspace_memory_confirmations_workspace_id"))
    op.drop_table("workspace_memory_confirmations")
