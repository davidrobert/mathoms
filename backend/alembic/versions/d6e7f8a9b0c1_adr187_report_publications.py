"""ADR-187: report_publications — mês fechado imutável.

Revision ID: d6e7f8a9b0c1
Revises: c5d6e7f8a9b0
Create Date: 2026-05-10

ADR-187 (A11.report-publication): introduz tabela ``report_publications``
como evento explícito, imutável e auditável de "relatório publicado /
mês fechado".

Default policy: workspace sem linha viva → mês NÃO está fechado. Backfill
manual opcional para clientes legados.

Soft-delete: ``unpublished_at IS NOT NULL`` significa "publicação foi
revogada" — nunca apagamos linha (auditoria). Unique parcial garante
no máximo 1 publicação viva por (workspace, period).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d6e7f8a9b0c1"
down_revision: Union[str, Sequence[str], None] = "c5d6e7f8a9b0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create ``report_publications`` with partial unique index on active rows."""
    op.create_table(
        "report_publications",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.String(length=36),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("period_yyyymm", sa.String(length=6), nullable=False),
        sa.Column(
            "artifact_id",
            sa.Integer(),
            sa.ForeignKey("pipeline_artifacts.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_by", sa.String(length=64), nullable=False),
        sa.Column("immutable_hash", sa.String(length=64), nullable=False),
        sa.Column("unpublished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "length(period_yyyymm) = 6",
            name="ck_report_publications_period_len",
        ),
    )
    op.create_index(
        "ix_report_publications_workspace_id",
        "report_publications",
        ["workspace_id"],
    )
    op.create_index(
        "ix_report_publications_workspace_period",
        "report_publications",
        ["workspace_id", "period_yyyymm"],
    )
    op.create_index(
        "uq_report_publications_active",
        "report_publications",
        ["workspace_id", "period_yyyymm"],
        unique=True,
        sqlite_where=sa.text("unpublished_at IS NULL"),
        postgresql_where=sa.text("unpublished_at IS NULL"),
    )


def downgrade() -> None:
    """Drop ``report_publications`` table and indices."""
    op.drop_index("uq_report_publications_active", table_name="report_publications")
    op.drop_index("ix_report_publications_workspace_period", table_name="report_publications")
    op.drop_index("ix_report_publications_workspace_id", table_name="report_publications")
    op.drop_table("report_publications")
