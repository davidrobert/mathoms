"""ADR-362 — executor_revision em pipeline_stage_logs.

Reversível por construção: coluna nullable, sem backfill, sem índice, sem
constraint. Em Postgres 11+ `ADD COLUMN NULL` é catalog-only — sem lock de
tabela e sem rewrite, o que importa porque a tabela cresce a cada run.

Sem índice de propósito: a query é `WHERE pipeline_run_id = :r`, já servida pelo
índice existente. A revisão é projeção, não filtro; índice entra quando existir
query que filtre por revisão.

Revision ID: adr362execrev
Revises: adr324supersede
"""

import sqlalchemy as sa
from alembic import op

revision = "adr362execrev"
down_revision = "adr324supersede"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "pipeline_stage_logs",
        sa.Column("executor_revision", sa.String(48), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("pipeline_stage_logs", "executor_revision")
