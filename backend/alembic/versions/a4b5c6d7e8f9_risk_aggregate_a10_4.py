"""adr-178 risks aggregate (workspace-scoped)

Revision ID: a4b5c6d7e8f9
Revises: f2b3c4d5e6a7
Create Date: 2026-05-07

ADR-178 (Sprint A10.4): introduz aggregate ``Risk`` workspace-scoped,
paralelo a ``Decision`` (ADR-136). Decision = ação a tomar; Risk =
evento incerto. Link causa↔mitigação via ``mitigations_decision_ids``
(JSON array de Decision.id).

Schema (ver `backend/app/models/risk.py`):
    risks(
        id, workspace_id FK, code, name, rationale,
        probability NULL, impact_level, impact_brl_cents NULL,
        status (default 'Ativo'), mitigations_decision_ids JSON,
        created_at, updated_at,
        UNIQUE (workspace_id, code)
    )

Money em ``BIGINT`` cents (ADR-090). Enums (probability/impact_level/
status) validados na application layer (frozensets em
`models/risk.py`); coluna é VARCHAR para portabilidade SQLite/Postgres.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a4b5c6d7e8f9"
down_revision: Union[str, None] = "f2b3c4d5e6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "risks",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("probability", sa.String(length=16), nullable=True),
        sa.Column("impact_level", sa.String(length=16), nullable=False),
        sa.Column("impact_brl_cents", sa.BigInteger(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("mitigations_decision_ids", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workspace_id", "code", name="uq_risks_workspace_code"),
    )
    with op.batch_alter_table("risks", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_risks_workspace_id"), ["workspace_id"], unique=False)
        batch_op.create_index("ix_risks_ws_status", ["workspace_id", "status"], unique=False)
        batch_op.create_index("ix_risks_ws_impact", ["workspace_id", "impact_level"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("risks", schema=None) as batch_op:
        batch_op.drop_index("ix_risks_ws_impact")
        batch_op.drop_index("ix_risks_ws_status")
        batch_op.drop_index(batch_op.f("ix_risks_workspace_id"))
    op.drop_table("risks")
