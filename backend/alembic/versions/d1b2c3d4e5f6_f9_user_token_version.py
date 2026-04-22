"""f9_user_token_version

Revision ID: d1b2c3d4e5f6
Revises: d0a1b2c3d4e5
Create Date: 2026-04-15

F9.2 · forced logout — adiciona `users.token_version` para invalidar
JWTs ao remover membership.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d1b2c3d4e5f6"
down_revision: Union[str, None] = "d0a1b2c3d4e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "token_version",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "token_version")
