"""adr283_report_patrimonio_liquido_numeric — Float → Numeric(18,2) (ADR-090/ADR-283). Agregado BRL consolidado, escalar — Numeric honra o invariante sem cents int. Postgres USING ::numeric(18,2) auto-arredonda; SQLite recria via batch.

Revision ID: a6b7c8d9e0f1
Revises: adr278datasourcefk
Create Date: 2026-06-09 19:10:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a6b7c8d9e0f1"
down_revision: Union[str, Sequence[str], None] = "adr278datasourcefk"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _reports_table(patrimonio_type: sa.types.TypeEngine) -> sa.Table:
    """Snapshot de ``reports`` para ``copy_from`` (batch offline-safe; sem reflection)."""
    md = sa.MetaData()
    return sa.Table(
        "reports",
        md,
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.String(length=36),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "pipeline_run_id",
            sa.String(length=36),
            sa.ForeignKey("pipeline_runs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("period", sa.String(length=50), nullable=True),
        sa.Column(
            "analysis_artifact_id",
            sa.Integer(),
            sa.ForeignKey("pipeline_artifacts.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("tasks_snapshot_json", sa.JSON(), nullable=True),
        sa.Column("premissas_snapshot_json", sa.JSON(), nullable=True),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("patrimonio_liquido", patrimonio_type, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def upgrade() -> None:
    with op.batch_alter_table(
        "reports", schema=None, copy_from=_reports_table(sa.Float())
    ) as batch_op:
        batch_op.alter_column(
            "patrimonio_liquido",
            existing_type=sa.Float(),
            type_=sa.Numeric(18, 2),
            existing_nullable=True,
            postgresql_using="patrimonio_liquido::numeric(18,2)",
        )


def downgrade() -> None:
    # Reversível com perda de precisão aceita (Numeric → Float).
    with op.batch_alter_table(
        "reports", schema=None, copy_from=_reports_table(sa.Numeric(18, 2))
    ) as batch_op:
        batch_op.alter_column(
            "patrimonio_liquido",
            existing_type=sa.Numeric(18, 2),
            type_=sa.Float(),
            existing_nullable=True,
            postgresql_using="patrimonio_liquido::double precision",
        )
