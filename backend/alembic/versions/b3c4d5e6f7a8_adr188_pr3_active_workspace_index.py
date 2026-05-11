"""ADR-188 A12 P3 PR3: partial index ix_txov_active_workspace (revision b3c4d5e6f7a8).

Read-path do learning loop e do E4 consulta ``transaction_overrides``
filtrando por ``workspace_id`` + ``deleted_at IS NULL`` (qualquer source).
Os índices UNIQUE existentes (``uq_txov_active_rule``) só cobrem
``source='rule'``; queries que olham ``source='manual'`` (sticky check)
ou ambas (view ``transaction_overrides_active``) fazem sequential scan.

Adiciona partial index cobrindo read-path:

    CREATE INDEX ix_txov_active_workspace
      ON transaction_overrides (workspace_id)
      WHERE deleted_at IS NULL

Justificativa data-eng (gate triple PR2 #197, ressalva R7).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b3c4d5e6f7a8"
down_revision: Union[str, Sequence[str], None] = "a2b3c4d5e6f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_txov_active_workspace",
        "transaction_overrides",
        ["workspace_id"],
        unique=False,
        sqlite_where=sa.text("deleted_at IS NULL"),
        postgresql_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_txov_active_workspace", table_name="transaction_overrides")
