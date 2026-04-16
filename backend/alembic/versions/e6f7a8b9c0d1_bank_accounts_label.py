"""bank_accounts label column (BUG-014)

Revision ID: e6f7a8b9c0d1
Revises: d1b2c3d4e5f6
Create Date: 2026-04-16

Adds optional human-readable label for bank account rows (ORM already had
the field; SQLite dev DBs failed with "no such column: bank_accounts.label").
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e6f7a8b9c0d1"
down_revision: Union[str, None] = "d1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("bank_accounts", schema=None) as batch_op:
        batch_op.add_column(sa.Column("label", sa.String(length=255), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("bank_accounts", schema=None) as batch_op:
        batch_op.drop_column("label")
