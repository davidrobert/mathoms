"""report_collab: tabelas report_notes + kanban_items (ADR-123 · Fase 6.5)

Persiste Notas (T6) e Kanban (T3) do relatório premium no backend em vez
de localStorage — permite multi-dispositivo + exportação. Continua
stateless rigoroso (ADR-111): estado vive no DB, não em memória.

Revision ID: t8u9v0w1x2y3
Revises: s7t8u9v0w1x2
Create Date: 2026-04-24
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "t8u9v0w1x2y3"
down_revision: Union[str, None] = "s7t8u9v0w1x2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "report_notes",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.String(length=36),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "report_id",
            sa.String(length=36),
            sa.ForeignKey("reports.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "author_user_id",
            sa.String(length=36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("content", sa.Text(), nullable=False, server_default=""),
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
        sa.UniqueConstraint("workspace_id", "report_id", name="uq_report_notes_ws_report"),
    )

    op.create_table(
        "kanban_items",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.String(length=36),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "report_id",
            sa.String(length=36),
            sa.ForeignKey("reports.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("titulo", sa.String(length=500), nullable=False),
        sa.Column("coluna", sa.String(length=32), nullable=False, server_default="a_fazer"),
        sa.Column("prioridade", sa.String(length=16), nullable=True),
        sa.Column("prazo", sa.Date(), nullable=True),
        sa.Column("categoria", sa.String(length=64), nullable=True),
        sa.Column("essencial", sa.String(length=1), nullable=True),
        sa.Column("ordem", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_by",
            sa.String(length=36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
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
    op.create_index(
        "ix_kanban_items_ws_report_col",
        "kanban_items",
        ["workspace_id", "report_id", "coluna"],
    )


def downgrade() -> None:
    op.drop_index("ix_kanban_items_ws_report_col", table_name="kanban_items")
    op.drop_table("kanban_items")
    op.drop_table("report_notes")
