"""ADR-173: monthly_llm_budget_usd nullable — NULL = sem cap (unlimited).

Revision ID: adr173budgetnull
Revises: rel03reportuniq
Create Date: 2026-07-02

Pré-ADR-173 a coluna era NOT NULL default 5.00 e alimentava apenas o alarme
do console admin. Com o hard-stop pré-call (110%) do ``LLMBudgetService``,
"sem budget" precisa ser representável: NULL = unlimited (default em
dev/staging via seed manual; workspaces existentes preservam 5.00).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "adr173budgetnull"
down_revision: Union[str, Sequence[str], None] = "rel03reportuniq"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("workspaces") as batch:
        batch.alter_column(
            "monthly_llm_budget_usd",
            existing_type=sa.Numeric(10, 2),
            nullable=True,
            existing_server_default=sa.text("'5.00'"),
        )


def downgrade() -> None:
    # NULL → 5.00 antes de reimpor NOT NULL (mesmo default pré-ADR-173).
    op.execute(
        "UPDATE workspaces SET monthly_llm_budget_usd = 5.00 "
        "WHERE monthly_llm_budget_usd IS NULL"
    )
    with op.batch_alter_table("workspaces") as batch:
        batch.alter_column(
            "monthly_llm_budget_usd",
            existing_type=sa.Numeric(10, 2),
            nullable=False,
            existing_server_default=sa.text("'5.00'"),
        )
