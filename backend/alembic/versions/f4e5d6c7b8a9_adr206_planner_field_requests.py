"""ADR-206 §D1 — planner_field_requests telemetria. Revision ID: f4e5d6c7b8a9 / Revises: e3d4e5f6a7b8 / Create Date: 2026-05-14."""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f4e5d6c7b8a9"
down_revision: Union[str, None] = "e3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_INDEXES = (
    ("ix_planner_field_requests_workspace_id", ["workspace_id"]),
    ("ix_planner_field_requests_planner_review_id", ["planner_review_id"]),
    ("ix_planner_field_requests_field_path", ["field_path"]),
    ("ix_planner_field_requests_created_at", ["created_at"]),
    ("ix_planner_field_requests_date_path", ["created_at", "field_path"]),
)


def upgrade() -> None:
    """Cria tabela ``planner_field_requests`` — telemetria M4 do parecer (ADR-206)."""
    op.create_table(
        "planner_field_requests",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("planner_review_id", sa.String(length=36), nullable=False),
        sa.Column("field_path", sa.String(length=255), nullable=False),
        sa.Column("motivo", sa.Text(), nullable=False),
        sa.Column("reason", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["planner_review_id"], ["planner_review_metadata.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "planner_review_id", "field_path", name="uq_planner_field_request_review_path"
        ),
    )
    with op.batch_alter_table("planner_field_requests") as batch_op:
        for name, cols in _INDEXES:
            batch_op.create_index(name, cols, unique=False)


def downgrade() -> None:
    """Drop tabela + índices."""
    with op.batch_alter_table("planner_field_requests") as batch_op:
        for name, _cols in reversed(_INDEXES):
            batch_op.drop_index(name)
    op.drop_table("planner_field_requests")
