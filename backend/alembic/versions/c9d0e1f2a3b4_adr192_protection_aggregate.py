"""adr-192 protection aggregate + risks.mitigation_protection_ids

Revision ID: c9d0e1f2a3b4
Revises: b3c4d5e6f7a8
Create Date: 2026-05-11

ADR-192 (Sprint A11.W5): introduz aggregate ``Protection`` paralelo a
``Risk`` (ADR-178) para modelar apólices contratadas. ``Risk`` ganha
``mitigation_protection_ids`` (lista N:N opaca, espelha
``mitigations_decision_ids``).

Schema (ver `backend/app/models/protection.py`):
    protections(
        id, workspace_id FK CASCADE, category, holder_family_member_id FK SET NULL,
        insurer, policy_ref (Fernet vault, app-layer), coverage_brl_cents BIGINT,
        premium_monthly_brl_cents BIGINT nullable, coverage_type nullable,
        starts_at, ends_at nullable, status, notes nullable,
        created_at, updated_at
    )
    + ix_protections_workspace_id
    + ix_protections_ws_status
    + ix_protections_ws_category
    + ix_protections_ws_ends_at  (viabiliza job futuro "vencendo em 30d")

    risks.mitigation_protection_ids JSON nullable (default NULL)
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c9d0e1f2a3b4"
down_revision: Union[str, None] = "b3c4d5e6f7a8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "protections",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("holder_family_member_id", sa.String(length=36), nullable=True),
        sa.Column("insurer", sa.String(length=120), nullable=True),
        sa.Column("policy_ref", sa.Text(), nullable=True),
        sa.Column("coverage_brl_cents", sa.BigInteger(), nullable=False),
        sa.Column("premium_monthly_brl_cents", sa.BigInteger(), nullable=True),
        sa.Column("coverage_type", sa.String(length=16), nullable=True),
        sa.Column("starts_at", sa.Date(), nullable=False),
        sa.Column("ends_at", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["holder_family_member_id"], ["family_members.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("protections", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_protections_workspace_id"), ["workspace_id"], unique=False
        )
        batch_op.create_index("ix_protections_ws_status", ["workspace_id", "status"], unique=False)
        batch_op.create_index(
            "ix_protections_ws_category", ["workspace_id", "category"], unique=False
        )
        batch_op.create_index(
            "ix_protections_ws_ends_at", ["workspace_id", "ends_at"], unique=False
        )

    with op.batch_alter_table("risks", schema=None) as batch_op:
        batch_op.add_column(sa.Column("mitigation_protection_ids", sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("risks", schema=None) as batch_op:
        batch_op.drop_column("mitigation_protection_ids")

    with op.batch_alter_table("protections", schema=None) as batch_op:
        batch_op.drop_index("ix_protections_ws_ends_at")
        batch_op.drop_index("ix_protections_ws_category")
        batch_op.drop_index("ix_protections_ws_status")
        batch_op.drop_index(batch_op.f("ix_protections_workspace_id"))
    op.drop_table("protections")
