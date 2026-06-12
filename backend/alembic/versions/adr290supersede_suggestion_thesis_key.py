"""adr-290 suggestion supersede-per-run — thesis_key + superseded_at/by_run_id

Revision ID: adr290supersede
Revises: adr279edges
Create Date: 2026-06-12

ADR-290 (B1/B2): colunas nullable para supersede-per-run de Suggestion
origin='llm' (parecer). Sem NOT NULL, sem backfill, sem UNIQUE sobre
thesis_key — unicidade de tese é lógica de service (padrão ADR-269).
Backfill dogfood é script internal_ops separado (PLAN-suggestion-lifecycle F4).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "adr290supersede"
down_revision: Union[str, None] = "adr279edges"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("suggestions", schema=None) as batch_op:
        batch_op.add_column(sa.Column("thesis_key", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("superseded_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("superseded_by_run_id", sa.String(length=36), nullable=True))
        batch_op.create_index("ix_sugagg_ws_thesis", ["workspace_id", "thesis_key"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("suggestions", schema=None) as batch_op:
        batch_op.drop_index("ix_sugagg_ws_thesis")
        batch_op.drop_column("superseded_by_run_id")
        batch_op.drop_column("superseded_at")
        batch_op.drop_column("thesis_key")
