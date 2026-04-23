"""users: coluna is_developer para gating de features de desenvolvedor

Adiciona `is_developer BOOLEAN NOT NULL DEFAULT FALSE` em `users`. Usado
para esconder atalhos/ferramentas internas (ex.: botão "Reclassificar
Despesas") de usuários finais, expondo-as apenas a contas dev.

Toggle operacional via `python -m backend.app.scripts.set_developer_flag`.

Revision ID: s7t8u9v0w1x2
Revises: r6s7t8u9v0w1
Create Date: 2026-04-23
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "s7t8u9v0w1x2"
down_revision: Union[str, None] = "r6s7t8u9v0w1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "is_developer",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "is_developer")
