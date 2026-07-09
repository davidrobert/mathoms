"""ADR-324: supersessão de PropertyIdentity (superseded_at + superseded_by_id).

Aditiva e fail-safe: colunas nullable, sem backfill na migration — o
backfill dos órfãos existentes é script dry-run-first em
``dev/backfill_property_supersession.py`` (padrão A33.l6: janela de
regressão zero entre migration e código). ``batch_alter_table`` com
snapshot ``copy_from`` (padrão adr173budgetnull): SQLite não adiciona FK
sem rebuild, e o snapshot dispensa reflection no ``--sql`` offline.

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


def _property_identity_table(*, with_supersession: bool) -> sa.Table:
    """Snapshot da tabela como criada em adr215residencia1 (shape inalterado desde)."""
    metadata = sa.MetaData()
    columns = [
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.String(length=36),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("titular_key", sa.String(length=64), nullable=False),
        sa.Column("codigo_rfb", sa.String(length=4), nullable=False),
        sa.Column("endereco_canonical", sa.String(length=255), nullable=True),
        sa.Column("first_seen_year", sa.Integer(), nullable=False),
        sa.Column("descricao_sample", sa.Text(), nullable=True),
        sa.Column("low_confidence", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    ]
    if with_supersession:
        columns.extend(_supersession_columns())
    table = sa.Table("property_identity", metadata, *columns)
    sa.Index("ix_property_identity_workspace_id", table.c.workspace_id)
    sa.Index(
        "ix_property_identity_lookup",
        table.c.workspace_id,
        table.c.titular_key,
        table.c.codigo_rfb,
        table.c.endereco_canonical,
    )
    return table


def _supersession_columns() -> list[sa.Column]:
    return [
        sa.Column("superseded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "superseded_by_id",
            sa.String(length=36),
            sa.ForeignKey("property_identity.id", ondelete="SET NULL", name=_FK_NAME),
            nullable=True,
        ),
    ]


def upgrade() -> None:
    with op.batch_alter_table(
        "property_identity",
        schema=None,
        copy_from=_property_identity_table(with_supersession=False),
    ) as batch:
        for column in _supersession_columns():
            batch.add_column(column)


def downgrade() -> None:
    with op.batch_alter_table(
        "property_identity",
        schema=None,
        copy_from=_property_identity_table(with_supersession=True),
    ) as batch:
        batch.drop_column("superseded_by_id")
        batch.drop_column("superseded_at")
