"""add_content_hash_to_documents

Revision ID: 2eb4d38ca788
Revises: c7d8e9f0a1b2
Create Date: 2026-04-14 18:09:30.002801
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "2eb4d38ca788"
down_revision: Union[str, None] = "c7d8e9f0a1b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("documents", schema=None) as batch_op:
        batch_op.add_column(sa.Column("content_hash", sa.String(length=64), nullable=True))
        batch_op.create_index(
            batch_op.f("ix_documents_content_hash"), ["content_hash"], unique=False
        )


def downgrade() -> None:
    with op.batch_alter_table("documents", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_documents_content_hash"))
        batch_op.drop_column("content_hash")
