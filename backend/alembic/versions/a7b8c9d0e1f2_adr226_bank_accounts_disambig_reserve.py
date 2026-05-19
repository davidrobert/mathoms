"""ADR-226 PR1: bank_accounts.workspace_id + is_joint + co_titulares reserve."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import MetaData, Table, text

revision: str = "a7b8c9d0e1f2"
down_revision: Union[str, Sequence[str], None] = "adr224assetcatalog"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _bank_accounts_pre() -> Table:
    """Snapshot pré-upgrade — colunas conforme ADR-146 (último a tocar bank_accounts)."""
    return Table(
        "bank_accounts",
        MetaData(),
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "member_id",
            sa.String(36),
            sa.ForeignKey("family_members.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("institution_code", sa.String(50), nullable=False),
        sa.Column("account_type", sa.String(100), nullable=False),
        sa.Column("agency", sa.String(20), nullable=True),
        sa.Column("account_number", sa.String(30), nullable=True),
        sa.Column("label", sa.String(255), nullable=True),
        sa.Column("source_tier", sa.SmallInteger(), nullable=True),
    )


def _add_columns_nullable() -> None:
    # workspace_id desnormalizado destrava partial unique index do PR4
    # (PostgreSQL não suporta JOIN em índice funcional).
    # is_joint + co_titulares: reservados para V2 ADR follow-up (rateio).
    with op.batch_alter_table("bank_accounts", copy_from=_bank_accounts_pre()) as batch:
        for col in _new_columns():
            batch.add_column(col)


def _backfill_workspace_id() -> None:
    # Idempotente; UPDATE com SELECT correlato garante valor consistente.
    # ON DELETE CASCADE em member_id já garante integridade (sem órfãs).
    op.execute(
        text(
            "UPDATE bank_accounts SET workspace_id = ("
            "SELECT family_members.workspace_id FROM family_members "
            "WHERE family_members.id = bank_accounts.member_id"
            ")"
        )
    )


def _new_columns() -> list[sa.Column]:
    return [
        sa.Column("workspace_id", sa.String(36), nullable=True),
        sa.Column("is_joint", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("co_titulares", sa.JSON(), nullable=True),
    ]


def _bank_accounts_after_add() -> Table:
    """Snapshot pós ADD COLUMN — usado para alter NOT NULL + FK + index."""
    t = _bank_accounts_pre()
    for col in _new_columns():
        t.append_column(col)
    return t


def _set_workspace_id_not_null_and_fk() -> None:
    with op.batch_alter_table("bank_accounts", copy_from=_bank_accounts_after_add()) as batch:
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


def _bank_accounts_full() -> Table:
    """Snapshot pós-upgrade completo — usado no downgrade."""
    t = _bank_accounts_after_add()
    return t


def downgrade() -> None:
    with op.batch_alter_table("bank_accounts", copy_from=_bank_accounts_full()) as batch:
        batch.drop_index("ix_bank_accounts_workspace_id")
        batch.drop_constraint("fk_bank_accounts_workspace_id", type_="foreignkey")
        batch.drop_column("co_titulares")
        batch.drop_column("is_joint")
        batch.drop_column("workspace_id")
