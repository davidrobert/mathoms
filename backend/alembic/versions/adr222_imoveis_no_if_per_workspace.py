"""ADR-222 A12: workspaces.imoveis_no_if + audit minimal.

Move o toggle `imoveis_no_if` de `config/pipeline.json` global para coluna
per-workspace, cumprindo o débito explicitado em ADR-142 §Consequências
("promessa de doc, não realidade") e ADR-215 §Follow-ups.

Mudanças:

1. ``workspaces.imoveis_no_if`` BOOLEAN NOT NULL DEFAULT true
2. ``workspaces.imoveis_no_if_set_at`` TIMESTAMPTZ NULL
3. ``workspaces.imoveis_no_if_set_by_user_id`` String(36) FK users.id ON DELETE SET NULL NULLABLE

Default `true` preserva comportamento atual (`pipeline.json:14` é `true`
hoje); cleanup do JSON vem em PR2 imediato (mesma sprint). `set_at IS NULL`
distingue "default migrado" de "escolha explícita".
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import MetaData, Table

revision: str = "adr222imoveisif"
down_revision: Union[str, Sequence[str], None] = "adr219wave1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _workspaces_pre() -> Table:
    """Snapshot pré-upgrade — antes das colunas desta ADR."""
    return Table(
        "workspaces",
        MetaData(),
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("family_surname", sa.String(255), nullable=True),
        sa.Column(
            "owner_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "monthly_llm_budget_usd",
            sa.Numeric(10, 2),
            nullable=False,
            server_default="5.00",
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("business_profile_json", sa.JSON(), nullable=True),
        sa.Column("rule_cap_override", sa.Integer(), nullable=True),
        sa.Column(
            "residencia_status",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'undeclared'"),
        ),
    )


def _workspaces_post() -> Table:
    """Snapshot pós-upgrade — com toggle imoveis_no_if + audit."""
    return Table(
        "workspaces",
        MetaData(),
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("family_surname", sa.String(255), nullable=True),
        sa.Column(
            "owner_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "monthly_llm_budget_usd",
            sa.Numeric(10, 2),
            nullable=False,
            server_default="5.00",
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("business_profile_json", sa.JSON(), nullable=True),
        sa.Column("rule_cap_override", sa.Integer(), nullable=True),
        sa.Column(
            "residencia_status",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'undeclared'"),
        ),
        sa.Column(
            "imoveis_no_if",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column("imoveis_no_if_set_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "imoveis_no_if_set_by_user_id",
            sa.String(36),
            sa.ForeignKey(
                "users.id",
                name="fk_workspaces_imoveis_no_if_set_by_user_id",
                ondelete="SET NULL",
            ),
            nullable=True,
        ),
    )


def upgrade() -> None:
    """Add imoveis_no_if + audit cols to workspaces (default true)."""
    with op.batch_alter_table("workspaces", copy_from=_workspaces_pre()) as batch_op:
        batch_op.add_column(
            sa.Column(
                "imoveis_no_if",
                sa.Boolean(),
                nullable=False,
                server_default=sa.true(),
            )
        )
        batch_op.add_column(
            sa.Column(
                "imoveis_no_if_set_at",
                sa.DateTime(timezone=True),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "imoveis_no_if_set_by_user_id",
                sa.String(36),
                sa.ForeignKey(
                    "users.id",
                    name="fk_workspaces_imoveis_no_if_set_by_user_id",
                    ondelete="SET NULL",
                ),
                nullable=True,
            )
        )


def downgrade() -> None:
    """Drop the 3 columns (reversible — preserved audit FK with SET NULL)."""
    with op.batch_alter_table("workspaces", copy_from=_workspaces_post()) as batch_op:
        batch_op.drop_column("imoveis_no_if_set_by_user_id")
        batch_op.drop_column("imoveis_no_if_set_at")
        batch_op.drop_column("imoveis_no_if")
