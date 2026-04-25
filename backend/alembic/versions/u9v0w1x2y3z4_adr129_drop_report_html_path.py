"""adr-129 drop report.html_path

Revision ID: u9v0w1x2y3z4
Revises: t8u9v0w1x2y3
Create Date: 2026-04-24

ADR-129: descontinuação completa do renderer HTML server-side. O campo
`reports.html_path` apontava para o HTML standalone gerado pelo E6, que
não é mais consumido por nenhuma rota (PDF via Playwright sobre o
relatório React é a única via de export server-side).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "u9v0w1x2y3z4"
down_revision: Union[str, None] = "t8u9v0w1x2y3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _reports_table_pre_drop() -> sa.Table:
    """Snapshot estático da tabela ``reports`` ANTES do drop, p/ offline SQL.

    Em modo ``--sql`` (sem conexão), Alembic não consegue refletir o schema
    e exige que `batch_alter_table` receba ``copy_from`` com o Table completo.
    """
    return sa.Table(
        "reports",
        sa.MetaData(),
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("workspace_id", sa.String(36), nullable=False),
        sa.Column("pipeline_run_id", sa.String(36), nullable=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("period", sa.String(50), nullable=True),
        sa.Column("html_path", sa.Text(), nullable=False),
        sa.Column("analysis_json_path", sa.Text(), nullable=True),
        sa.Column("tasks_snapshot_json", sa.JSON(), nullable=True),
        sa.Column("premissas_snapshot_json", sa.JSON(), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("patrimonio_liquido", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def _reports_table_post_drop() -> sa.Table:
    return sa.Table(
        "reports",
        sa.MetaData(),
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("workspace_id", sa.String(36), nullable=False),
        sa.Column("pipeline_run_id", sa.String(36), nullable=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("period", sa.String(50), nullable=True),
        sa.Column("analysis_json_path", sa.Text(), nullable=True),
        sa.Column("tasks_snapshot_json", sa.JSON(), nullable=True),
        sa.Column("premissas_snapshot_json", sa.JSON(), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("patrimonio_liquido", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def upgrade() -> None:
    with op.batch_alter_table("reports", copy_from=_reports_table_pre_drop()) as batch_op:
        batch_op.drop_column("html_path")


def downgrade() -> None:
    # ADR-129: downgrade só restaura schema, não o dado.
    with op.batch_alter_table("reports", copy_from=_reports_table_post_drop()) as batch_op:
        batch_op.add_column(sa.Column("html_path", sa.Text(), nullable=True))
