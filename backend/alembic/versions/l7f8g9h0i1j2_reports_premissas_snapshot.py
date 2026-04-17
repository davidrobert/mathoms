"""reports: premissas_snapshot_json (F11.6b)

Snapshot mínimo das premissas vigentes + hash do goals.json materializado
para comparação mês a mês.

Revision ID: l7f8g9h0i1j2
Revises: k6e7f8a9b0c1
Create Date: 2026-04-17
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "l7f8g9h0i1j2"
down_revision: Union[str, None] = "k6e7f8a9b0c1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "reports",
        sa.Column("premissas_snapshot_json", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("reports", "premissas_snapshot_json")
