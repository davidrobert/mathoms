"""adr-267 task_suggestions dedup_key + soft-supersede (Revision: adr267tsdedup, Revises: a17l6tedfix, Create Date: 2026-05-23). Adiciona dedup_key (sha256 normalizado), superseded_at, superseded_by_run_id + índice parcial ix_tsugg_ws_dedup_active filtrado por status IN ('pending','approved')."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "adr267tsdedup"
down_revision: Union[str, None] = "a17l6tedfix"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("task_suggestions", schema=None) as batch_op:
        batch_op.add_column(sa.Column("dedup_key", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("superseded_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("superseded_by_run_id", sa.String(length=36), nullable=True))
    # Índice parcial — SQLite 3.8+ e Postgres suportam WHERE em CREATE INDEX.
    # Lookup do dispatcher é sempre (workspace_id, dedup_key) filtrado por
    # status ativo; histórico ('rejected', 'merged', 'superseded') não conta
    # para colisão de dedup ativa.
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_tsugg_ws_dedup_active
        ON task_suggestions (workspace_id, dedup_key)
        WHERE status IN ('pending', 'approved')
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_tsugg_ws_dedup_active")
    with op.batch_alter_table("task_suggestions", schema=None) as batch_op:
        batch_op.drop_column("superseded_by_run_id")
        batch_op.drop_column("superseded_at")
        batch_op.drop_column("dedup_key")
