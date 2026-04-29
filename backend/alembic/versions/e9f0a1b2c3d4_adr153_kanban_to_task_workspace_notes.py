"""ADR-153 (M1): Task expand (board_*, origin_report_id) + workspace_notes table.

Revision ID: e9f0a1b2c3d4
Revises: d8e9f0a1b2c3
Create Date: 2026-04-29

ADR-153 (Direção E · Onda 1): funde ``KanbanItem`` (ADR-123) no aggregate
``Task`` (ADR-074) e migra ``ReportNotes`` (ADR-123) para ``workspace_notes``
(workspace-scoped, multi-row, opcionalmente fixadas).

Esta é a migration **M1 — additive** (zero-downtime). Apenas adiciona
colunas nullable em ``tasks`` e cria ``workspace_notes``. Tabelas
legadas ``kanban_items`` e ``report_notes`` permanecem intactas até
**M2** (sprint+1, em PR separado), após validação em prod.

Backfill de dados (kanban_items → tasks, report_notes → workspace_notes)
roda separado via ``dev/migrate_kanban_to_task.py`` — idempotente,
re-executável.

Campos adicionados em ``tasks``:
- ``board_column``: 'a_fazer'|'em_andamento'|'concluido', NULL para
  tasks que não vivem no Kanban view (default).
- ``board_order``: ordem dentro da coluna (DnD).
- ``origin_report_id``: FK→reports ON DELETE SET NULL — rastreia origem
  da task quando criada por backfill ou aceita de Kanban view.
- ``urgency``: 'alta'|'media'|'baixa' NULL — eixo tático ortogonal a
  ``priority`` (S/R/O metodológico).
- ``is_board_only``: BOOLEAN NOT NULL DEFAULT false — quando true,
  widgets como ``UpcomingTasksWidget`` filtram a task fora (evita
  inflar lista após backfill de Kanban).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e9f0a1b2c3d4"
down_revision: Union[str, None] = "d8e9f0a1b2c3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("tasks") as batch:
        batch.add_column(sa.Column("board_column", sa.String(length=32), nullable=True))
        batch.add_column(sa.Column("board_order", sa.Integer(), nullable=True))
        batch.add_column(
            sa.Column(
                "origin_report_id",
                sa.String(length=36),
                nullable=True,
            )
        )
        batch.add_column(sa.Column("urgency", sa.String(length=8), nullable=True))
        batch.add_column(
            sa.Column(
                "is_board_only",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )
        batch.create_foreign_key(
            "fk_tasks_origin_report",
            "reports",
            ["origin_report_id"],
            ["id"],
            ondelete="SET NULL",
        )

    op.create_index(
        "ix_tasks_ws_board_column",
        "tasks",
        ["workspace_id", "board_column"],
    )

    op.create_table(
        "workspace_notes",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.String(length=36),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("title", sa.String(length=200), nullable=True),
        sa.Column("content", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "pinned",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "author_user_id",
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
        "ix_workspace_notes_ws_pinned_updated",
        "workspace_notes",
        ["workspace_id", "pinned", "updated_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_workspace_notes_ws_pinned_updated", table_name="workspace_notes")
    op.drop_table("workspace_notes")

    op.drop_index("ix_tasks_ws_board_column", table_name="tasks")
    with op.batch_alter_table("tasks") as batch:
        batch.drop_constraint("fk_tasks_origin_report", type_="foreignkey")
        batch.drop_column("is_board_only")
        batch.drop_column("urgency")
        batch.drop_column("origin_report_id")
        batch.drop_column("board_order")
        batch.drop_column("board_column")
