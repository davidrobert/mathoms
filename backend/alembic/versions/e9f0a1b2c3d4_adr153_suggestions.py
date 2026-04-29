"""adr-153 suggestions aggregate (Direção E · Onda 5)

Revision ID: e9f0a1b2c3d4
Revises: d8e9f0a1b2c3
Create Date: 2026-04-29

ADR-153: introduz aggregate ``Suggestion`` (proposta determinística
imutável + state machine simples). Ver `backend/app/models/suggestion.py`.

Schema:
    suggestions(
        id, workspace_id FK, report_id FK SET NULL,
        section_id, kind, origin, severity, title, rationale,
        amount_brl_cents, dedup_key,
        status, accepted_decision_id FK SET NULL, dismissed_reason,
        accepted_at, dismissed_at,
        created_at, updated_at,
        UNIQUE (workspace_id, dedup_key, status)
    )

Money em BIGINT cents (ADR-090). ``status``/``severity``/``origin``/
``dismissed_reason``/``kind`` validados em service layer (frozenset
em `models/suggestion.py`).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e9f0a1b2c3d4"
down_revision: Union[str, None] = "d8e9f0a1b2c3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "suggestions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("report_id", sa.String(length=36), nullable=True),
        sa.Column("section_id", sa.String(length=32), nullable=False),
        sa.Column("kind", sa.String(length=64), nullable=False),
        sa.Column("origin", sa.String(length=32), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("amount_brl_cents", sa.BigInteger(), nullable=True),
        sa.Column("dedup_key", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("accepted_decision_id", sa.String(length=36), nullable=True),
        sa.Column("dismissed_reason", sa.String(length=32), nullable=True),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dismissed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["report_id"], ["reports.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["accepted_decision_id"], ["decisions.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "workspace_id",
            "dedup_key",
            "status",
            name="uq_sugagg_ws_dedup_status",
        ),
    )
    with op.batch_alter_table("suggestions", schema=None) as batch_op:
        batch_op.create_index("ix_sugagg_workspace_id", ["workspace_id"], unique=False)
        batch_op.create_index(
            "ix_sugagg_ws_status", ["workspace_id", "status"], unique=False
        )
        batch_op.create_index(
            "ix_sugagg_ws_dedup", ["workspace_id", "dedup_key"], unique=False
        )
        batch_op.create_index(
            "ix_sugagg_ws_section",
            ["workspace_id", "section_id"],
            unique=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("suggestions", schema=None) as batch_op:
        batch_op.drop_index("ix_sugagg_ws_section")
        batch_op.drop_index("ix_sugagg_ws_dedup")
        batch_op.drop_index("ix_sugagg_ws_status")
        batch_op.drop_index("ix_sugagg_workspace_id")
    op.drop_table("suggestions")
