"""A33.l6 — coluna retention_until em pipeline_artifacts (W6-T05, ADR-212).

Revision ID: a33l6retention
Revises: a32l5promptver
Create Date: 2026-07-07

Retenção por idade de row superseded. Coluna nullable com semântica
fail-safe: NULL = nunca prunável. Rows existentes ficam NULL — o backfill
é contínuo e roda dentro da task ``fin.prune_pipeline_artifacts`` (marca
apenas rows comprovadamente superseded, alias-aware), nunca nesta
migration, para não abrir janela em que rows correntes ganhem data por
engano antes do write-path novo estar no ar.

Índice parcial (``WHERE retention_until IS NOT NULL``) serve o predicado
do prune diário; a maioria das rows é NULL (corrente/fail-safe).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a33l6retention"
down_revision: Union[str, Sequence[str], None] = "a32l5promptver"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_INDEX_NAME = "ix_pipeline_artifacts_retention_until"


def upgrade() -> None:
    op.add_column(
        "pipeline_artifacts",
        sa.Column("retention_until", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        _INDEX_NAME,
        "pipeline_artifacts",
        ["retention_until"],
        postgresql_where=sa.text("retention_until IS NOT NULL"),
        sqlite_where=sa.text("retention_until IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index(_INDEX_NAME, table_name="pipeline_artifacts")
    with op.batch_alter_table("pipeline_artifacts") as batch_op:
        batch_op.drop_column("retention_until")
