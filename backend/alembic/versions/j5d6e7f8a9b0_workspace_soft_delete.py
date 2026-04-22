"""workspaces: add deleted_at for soft-delete (P1.2)

Soft-delete prevents irreversible data loss when a user accidentally
deletes a workspace. The tenancy dependency (`get_current_workspace`)
filters rows where `deleted_at IS NOT NULL`, so deleted workspaces
become inaccessible while data is preserved for recovery.

A janitor job (not implemented here) can hard-delete after a grace
period (30 days).

Revision ID: j5d6e7f8a9b0
Revises: i4c5d6e7f8a9
Create Date: 2026-04-16
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "j5d6e7f8a9b0"
down_revision: Union[str, Sequence[str], None] = "i4c5d6e7f8a9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("workspaces") as batch_op:
        batch_op.add_column(sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.create_index("ix_workspaces_deleted_at", ["deleted_at"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("workspaces") as batch_op:
        batch_op.drop_index("ix_workspaces_deleted_at")
        batch_op.drop_column("deleted_at")
