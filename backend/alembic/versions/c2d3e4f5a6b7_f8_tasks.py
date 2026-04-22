"""f8_tasks

Revision ID: c2d3e4f5a6b7
Revises: b1c2d3e4f5a6
Create Date: 2026-04-15

ADR-074 — Tasks como entidade de 1ª classe.

Cria 3 tabelas:
- `tasks`: backlog ativo do workspace (priority/status/deadline/deps)
- `task_suggestions`: queue do E5.N aguardando aprovação humana
- `task_attachments`: anexos (comprovantes) referenciando storage

Migração one-shot do `config/tarefas.md` (43 tarefas + 2 concluídas)
roda separadamente via `backend/app/scripts/seed_tasks_ferreira_campos.py`.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c2d3e4f5a6b7"
down_revision: Union[str, None] = "b1c2d3e4f5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ─── tasks ──────────────────────────────────────────────────────
    op.create_table(
        "tasks",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.String(length=36),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("priority", sa.String(length=1), nullable=False),
        sa.Column(
            "deadline_kind",
            sa.String(length=32),
            nullable=False,
            server_default=sa.text("'UNSCHEDULED'"),
        ),
        sa.Column("deadline_date", sa.Date(), nullable=True),
        sa.Column("deadline_label", sa.String(length=128), nullable=True),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column("status_reason", sa.Text(), nullable=True),
        sa.Column("ref", sa.String(length=255), nullable=True),
        sa.Column(
            "parent_task_id",
            sa.String(length=36),
            sa.ForeignKey("tasks.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("related_transaction_id", sa.String(length=36), nullable=True),
        sa.Column(
            "related_goal_id",
            sa.String(length=36),
            sa.ForeignKey("goals.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "assigned_to",
            sa.String(length=36),
            sa.ForeignKey("family_members.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_from",
            sa.String(length=32),
            nullable=False,
            server_default=sa.text("'manual'"),
        ),
        sa.Column("source_suggestion_id", sa.String(length=36), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.UniqueConstraint("workspace_id", "number", name="uq_task_ws_number"),
    )
    op.create_index("ix_tasks_workspace_id", "tasks", ["workspace_id"])
    op.create_index("ix_tasks_category", "tasks", ["category"])
    op.create_index("ix_tasks_priority", "tasks", ["priority"])
    op.create_index("ix_tasks_deadline_date", "tasks", ["deadline_date"])
    op.create_index("ix_tasks_status", "tasks", ["status"])
    op.create_index("ix_tasks_parent_task_id", "tasks", ["parent_task_id"])
    op.create_index(
        "ix_tasks_ws_status_deadline",
        "tasks",
        ["workspace_id", "status", "deadline_date"],
    )
    op.create_index(
        "ix_tasks_ws_priority_status",
        "tasks",
        ["workspace_id", "priority", "status"],
    )

    # ─── task_suggestions ───────────────────────────────────────────
    op.create_table(
        "task_suggestions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.String(length=36),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("proposed_payload", sa.JSON(), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("source_run_id", sa.String(length=36), nullable=True),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column(
            "approved_task_id",
            sa.String(length=36),
            sa.ForeignKey("tasks.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "reviewed_by",
            sa.String(length=36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_suggestions_workspace_id", "task_suggestions", ["workspace_id"])
    op.create_index(
        "ix_suggestions_ws_status",
        "task_suggestions",
        ["workspace_id", "status"],
    )

    # ─── task_attachments ───────────────────────────────────────────
    op.create_table(
        "task_attachments",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "task_id",
            sa.String(length=36),
            sa.ForeignKey("tasks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "workspace_id",
            sa.String(length=36),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("storage_path", sa.String(length=500), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=128), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column(
            "uploaded_by",
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
    )
    op.create_index("ix_task_attachments_task_id", "task_attachments", ["task_id"])
    op.create_index(
        "ix_task_attachments_workspace_id",
        "task_attachments",
        ["workspace_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_task_attachments_workspace_id", table_name="task_attachments")
    op.drop_index("ix_task_attachments_task_id", table_name="task_attachments")
    op.drop_table("task_attachments")

    op.drop_index("ix_suggestions_ws_status", table_name="task_suggestions")
    op.drop_index("ix_suggestions_workspace_id", table_name="task_suggestions")
    op.drop_table("task_suggestions")

    op.drop_index("ix_tasks_ws_priority_status", table_name="tasks")
    op.drop_index("ix_tasks_ws_status_deadline", table_name="tasks")
    op.drop_index("ix_tasks_parent_task_id", table_name="tasks")
    op.drop_index("ix_tasks_status", table_name="tasks")
    op.drop_index("ix_tasks_deadline_date", table_name="tasks")
    op.drop_index("ix_tasks_priority", table_name="tasks")
    op.drop_index("ix_tasks_category", table_name="tasks")
    op.drop_index("ix_tasks_workspace_id", table_name="tasks")
    op.drop_table("tasks")
