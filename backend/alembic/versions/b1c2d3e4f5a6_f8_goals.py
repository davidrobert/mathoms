"""f8_goals

Revision ID: b1c2d3e4f5a6
Revises: a9b8c7d6e5f4
Create Date: 2026-04-15

ADR-073 — Goals como entidade versionada.

Cria a tabela `goals` com:
- `params_json` (JSONB com inputs do usuário: renda_passiva, trs, horizonte)
- `derived_json` (snapshot dos valores derivados: if_meta, aporte_necessario)
- `effective_from` / `effective_to` (versionamento temporal; `to IS NULL` = vigente)
- `is_template` (flag para seed de novos workspaces — força wizard)

Não faz backfill automático. Seeds específicos (Ferreira Campos +
template para novos workspaces) rodam por scripts em
`backend/app/scripts/seed_*.py`.
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b1c2d3e4f5a6"
down_revision: Union[str, None] = "a9b8c7d6e5f4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "goals",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.String(length=36),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("type", sa.String(length=64), nullable=False),
        sa.Column("params_json", sa.JSON(), nullable=False),
        sa.Column("derived_json", sa.JSON(), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column(
            "created_by",
            sa.String(length=36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "is_template",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_goals_workspace_id", "goals", ["workspace_id"])
    op.create_index("ix_goals_type", "goals", ["type"])
    op.create_index("ix_goals_effective_from", "goals", ["effective_from"])
    op.create_index(
        "ix_goals_ws_type_effective_to",
        "goals",
        ["workspace_id", "type", "effective_to"],
    )
    op.create_index(
        "ix_goals_ws_type_effective_from",
        "goals",
        ["workspace_id", "type", "effective_from"],
    )

    # Garantia de unicidade do registro vigente:
    # único por (workspace_id, type) quando effective_to IS NULL.
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ux_goals_current_ws_type
        ON goals (workspace_id, type)
        WHERE effective_to IS NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ux_goals_current_ws_type")
    op.drop_index("ix_goals_ws_type_effective_from", table_name="goals")
    op.drop_index("ix_goals_ws_type_effective_to", table_name="goals")
    op.drop_index("ix_goals_effective_from", table_name="goals")
    op.drop_index("ix_goals_type", table_name="goals")
    op.drop_index("ix_goals_workspace_id", table_name="goals")
    op.drop_table("goals")
