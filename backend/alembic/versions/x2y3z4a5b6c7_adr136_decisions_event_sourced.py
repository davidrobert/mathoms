"""adr-136 decisions + decision_events (event-sourced aggregate)

Revision ID: x2y3z4a5b6c7
Revises: w1x2y3z4a5b6
Create Date: 2026-04-27

ADR-136 (A7.2a): introduz aggregate ``Decision`` event-sourced para
substituir ``config/decisions.md``. Estado projetado em ``decisions``;
histórico append-only em ``decision_events``.

Schema (ver `backend/app/models/decision.py`):
    decisions(
        id, workspace_id FK, code, title, rationale, amount_brl_cents,
        status, supersedes_id (self-FK), decided_at, executed_at,
        created_at, updated_at,
        UNIQUE (workspace_id, code)
    )
    decision_events(
        id, decision_id FK, event_type, occurred_at, actor, payload jsonb
    )

Money sempre em ``BIGINT`` cents (ADR-090). ``status`` é texto livre
validado no service layer (frozenset em `models/decision.py`).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "x2y3z4a5b6c7"
down_revision: Union[str, None] = "w1x2y3z4a5b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "decisions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("code", sa.String(length=16), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("amount_brl_cents", sa.BigInteger(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("supersedes_id", sa.String(length=36), nullable=True),
        sa.Column("decided_at", sa.Date(), nullable=True),
        sa.Column("executed_at", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["supersedes_id"], ["decisions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workspace_id", "code", name="uq_decisions_workspace_code"),
    )
    with op.batch_alter_table("decisions", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_decisions_workspace_id"), ["workspace_id"], unique=False
        )
        batch_op.create_index("ix_decisions_ws_status", ["workspace_id", "status"], unique=False)

    op.create_table(
        "decision_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("decision_id", sa.String(length=36), nullable=False),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor", sa.String(length=128), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["decision_id"], ["decisions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("decision_events", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_decision_events_decision_id"),
            ["decision_id"],
            unique=False,
        )
        batch_op.create_index(
            "ix_decision_events_decision_occurred",
            ["decision_id", "occurred_at"],
            unique=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("decision_events", schema=None) as batch_op:
        batch_op.drop_index("ix_decision_events_decision_occurred")
        batch_op.drop_index(batch_op.f("ix_decision_events_decision_id"))
    op.drop_table("decision_events")

    with op.batch_alter_table("decisions", schema=None) as batch_op:
        batch_op.drop_index("ix_decisions_ws_status")
        batch_op.drop_index(batch_op.f("ix_decisions_workspace_id"))
    op.drop_table("decisions")
