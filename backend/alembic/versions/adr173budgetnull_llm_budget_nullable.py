"""ADR-173: monthly_llm_budget_usd nullable — NULL = sem cap (unlimited).

Revision ID: adr173budgetnull
Revises: rel03reportuniq
Create Date: 2026-07-02

Pré-ADR-173 a coluna era NOT NULL default 5.00 e alimentava apenas o alarme
do console admin. Com o hard-stop pré-call (110%) do ``LLMBudgetService``,
"sem budget" precisa ser representável: NULL = unlimited (default em
dev/staging via seed manual; workspaces existentes preservam 5.00).

SQLite reconstrói a tabela via batch; ``copy_from`` com snapshot completo
mantém o ``--sql`` offline funcional (precedente a6b7c8d9e0f1 / ADR-283).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "adr173budgetnull"
down_revision: Union[str, Sequence[str], None] = "rel03reportuniq"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _workspaces_table(budget_nullable: bool) -> sa.Table:
    """Snapshot de ``workspaces`` para ``copy_from`` (batch offline-safe; sem reflection)."""
    md = sa.MetaData()
    return sa.Table(
        "workspaces",
        md,
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("family_surname", sa.String(length=255), nullable=True),
        sa.Column(
            "owner_id",
            sa.String(length=36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "monthly_llm_budget_usd",
            sa.Numeric(10, 2),
            nullable=budget_nullable,
            server_default="5.00",
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("business_profile_json", sa.JSON(), nullable=True),
        sa.Column("rule_cap_override", sa.Integer(), nullable=True),
        sa.Column(
            "residencia_status",
            sa.String(length=20),
            nullable=False,
            server_default="undeclared",
        ),
        sa.Column("imoveis_no_if", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("imoveis_no_if_set_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "imoveis_no_if_set_by_user_id",
            sa.String(length=36),
            sa.ForeignKey(
                "users.id",
                name="fk_workspaces_imoveis_no_if_set_by_user_id",
                ondelete="SET NULL",
            ),
            nullable=True,
        ),
    )


def upgrade() -> None:
    with op.batch_alter_table(
        "workspaces", schema=None, copy_from=_workspaces_table(budget_nullable=False)
    ) as batch:
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
    with op.batch_alter_table(
        "workspaces", schema=None, copy_from=_workspaces_table(budget_nullable=True)
    ) as batch:
        batch.alter_column(
            "monthly_llm_budget_usd",
            existing_type=sa.Numeric(10, 2),
            nullable=False,
            existing_server_default=sa.text("'5.00'"),
        )
