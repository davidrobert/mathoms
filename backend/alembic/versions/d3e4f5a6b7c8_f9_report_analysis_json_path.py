"""f9_report_analysis_json_path

Revision ID: d3e4f5a6b7c8
Revises: c2d3e4f5a6b7
Create Date: 2026-04-15 14:00:00.000000

Adiciona `reports.analysis_json_path` para suportar o render nativo React
do relatório (ADR-076 / F9). Nullable para backward-compat com relatórios
pré-F9 que tinham apenas html_path.

NOTA: Originalmente esta migration tinha revision="c2d3e4f5a6b7" colidindo
com c2d3e4f5a6b7_f8_tasks.py (mesmo ID gerado por engano). Renumerada para
d3e4f5a6b7c8 e re-pendurada após c2d3e4f5a6b7 (F8 tasks).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d3e4f5a6b7c8"
down_revision: Union[str, None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "reports",
        sa.Column("analysis_json_path", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("reports", "analysis_json_path")
