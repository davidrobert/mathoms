"""adr283_drop_categories_monthly_cap — DROP COLUMN categories.monthly_cap (ADR-283 §B · A12.cat-legacy-sunset 2/2).

Float monetário legado órfão; cap canônico vive em
workspace_category_overrides.monthly_cap_brl_cents (BigInteger/cents, ADR-137).
O código parou de referenciar a coluna no PR #573 (deploy anterior) — ordem
obrigatória para zero-downtime: pods do deploy N-1 já não mapeiam a coluna
quando este DROP roda. Em Postgres o batch vira ALTER TABLE nativo; em SQLite
recria via "move and copy" com snapshot copy_from (offline-safe, sem reflection).

Revision ID: f2a3b4c5d6e7
Revises: a6b7c8d9e0f1
Create Date: 2026-06-09 21:45:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f2a3b4c5d6e7"
down_revision: Union[str, Sequence[str], None] = "a6b7c8d9e0f1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _categories_table(*, with_monthly_cap: bool) -> sa.Table:
    """Snapshot de ``categories`` para ``copy_from`` (batch offline-safe; sem reflection)."""
    md = sa.MetaData()
    cols = [
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.String(length=36),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("category_type", sa.String(length=10), nullable=False),
    ]
    if with_monthly_cap:
        cols.append(sa.Column("monthly_cap", sa.Float(), nullable=True))
    cols.extend(
        [
            sa.Column("order", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        ]
    )
    return sa.Table("categories", md, *cols)


def upgrade() -> None:
    with op.batch_alter_table(
        "categories", schema=None, copy_from=_categories_table(with_monthly_cap=True)
    ) as batch_op:
        batch_op.drop_column("monthly_cap")


def downgrade() -> None:
    # Recria a coluna vazia — valores do cap legado não são restauráveis
    # (perda documentada e aceita; o cap canônico em
    # workspace_category_overrides.monthly_cap_brl_cents fica intocado).
    with op.batch_alter_table(
        "categories", schema=None, copy_from=_categories_table(with_monthly_cap=False)
    ) as batch_op:
        batch_op.add_column(sa.Column("monthly_cap", sa.Float(), nullable=True))
