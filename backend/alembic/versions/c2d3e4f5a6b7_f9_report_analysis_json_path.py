"""f9_report_analysis_json_path

Revision ID: c2d3e4f5a6b7
Revises: b1c2d3e4f5a6
Create Date: 2026-04-15 14:00:00.000000

Adiciona `reports.analysis_json_path` para suportar o render nativo React
do relatório (ADR-076 / F9). Nullable para backward-compat com relatórios
pré-F9 que tinham apenas html_path.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c2d3e4f5a6b7"
down_revision: Union[str, None] = "b1c2d3e4f5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "reports",
        sa.Column("analysis_json_path", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("reports", "analysis_json_path")
