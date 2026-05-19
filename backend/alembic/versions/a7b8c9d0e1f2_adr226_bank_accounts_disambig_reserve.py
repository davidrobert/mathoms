"""ADR-226 PR1: bank_accounts.workspace_id + is_joint + co_titulares reserve."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

revision: str = "a7b8c9d0e1f2"
down_revision: Union[str, Sequence[str], None] = "adr224assetcatalog"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _add_columns_nullable() -> None:
    # workspace_id desnormalizado destrava partial unique index do PR4
    # (PostgreSQL não suporta JOIN em índice funcional).
    # is_joint + co_titulares: reservados para V2 ADR follow-up (rateio).
    with op.batch_alter_table("bank_accounts") as batch:
        batch.add_column(sa.Column("workspace_id", sa.String(length=36), nullable=True))
        batch.add_column(
            sa.Column("is_joint", sa.Boolean(), nullable=False, server_default=sa.false())
        )
        batch.add_column(sa.Column("co_titulares", sa.JSON(), nullable=True))


def _backfill_workspace_id() -> None:
    # Idempotente; UPDATE com SELECT correlato garante valor consistente
    # ON DELETE CASCADE em member_id já garante integridade (sem órfãs).
    op.execute(
        text(
            "UPDATE bank_accounts SET workspace_id = ("
            "SELECT family_members.workspace_id FROM family_members "
            "WHERE family_members.id = bank_accounts.member_id"
            ")"
        )
    )


def _set_workspace_id_not_null_and_fk() -> None:
    with op.batch_alter_table("bank_accounts") as batch:
        batch.alter_column("workspace_id", existing_type=sa.String(length=36), nullable=False)
        batch.create_foreign_key(
            "fk_bank_accounts_workspace_id",
            "workspaces",
            ["workspace_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch.create_index("ix_bank_accounts_workspace_id", ["workspace_id"], unique=False)


def upgrade() -> None:
    _add_columns_nullable()
    _backfill_workspace_id()
    _set_workspace_id_not_null_and_fk()


def downgrade() -> None:
    with op.batch_alter_table("bank_accounts") as batch:
        batch.drop_index("ix_bank_accounts_workspace_id")
        batch.drop_constraint("fk_bank_accounts_workspace_id", type_="foreignkey")
        batch.drop_column("co_titulares")
        batch.drop_column("is_joint")
        batch.drop_column("workspace_id")
