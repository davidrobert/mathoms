"""ADR-324: supersessão de PropertyIdentity (superseded_at + superseded_by_id).

Aditiva e fail-safe: colunas nullable, sem backfill na migration — o
backfill dos órfãos existentes é script dry-run-first em
``dev/backfill_property_supersession.py`` (padrão A33.l6: janela de
regressão zero entre migration e código).

Revision ID: adr324supersede
Revises: a33l2ptax3112
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "adr324supersede"
down_revision = "a33l2ptax3112"
branch_labels = None
depends_on = None

_FK_NAME = "fk_property_identity_superseded_by"


def upgrade() -> None:
    with op.batch_alter_table("property_identity") as batch:
        batch.add_column(sa.Column("superseded_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("superseded_by_id", sa.String(36), nullable=True))
        batch.create_foreign_key(
            _FK_NAME,
            "property_identity",
            ["superseded_by_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    with op.batch_alter_table("property_identity") as batch:
        batch.drop_constraint(_FK_NAME, type_="foreignkey")
        batch.drop_column("superseded_by_id")
        batch.drop_column("superseded_at")
