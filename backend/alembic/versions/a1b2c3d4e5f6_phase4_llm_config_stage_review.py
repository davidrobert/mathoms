"""phase4_llm_config_stage_review

Revision ID: a1b2c3d4e5f6
Revises: da5a6af13e3e
Create Date: 2026-04-14 18:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "da5a6af13e3e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "llm_configs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("api_key_encrypted", sa.Text(), nullable=False),
        sa.Column("model_name", sa.String(length=100), nullable=False),
        sa.Column("max_tokens", sa.Integer(), nullable=False),
        sa.Column("temperature", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("llm_configs") as batch_op:
        batch_op.create_index("ix_llm_configs_workspace_id", ["workspace_id"], unique=True)

    op.create_table(
        "stage_reviews",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("pipeline_run_id", sa.String(length=36), nullable=False),
        sa.Column("stage", sa.String(length=50), nullable=False),
        sa.Column(
            "status",
            sa.Enum("pending", "approved", "edited", name="stagereviewstatus"),
            nullable=False,
        ),
        sa.Column("original_output_json", sa.JSON(), nullable=True),
        sa.Column("edited_output_json", sa.JSON(), nullable=True),
        sa.Column("validation_errors", sa.Text(), nullable=True),
        sa.Column("reviewer_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["pipeline_run_id"], ["pipeline_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("stage_reviews") as batch_op:
        batch_op.create_index("ix_stage_reviews_pipeline_run_id", ["pipeline_run_id"], unique=False)

    with op.batch_alter_table("pipeline_runs") as batch_op:
        batch_op.add_column(
            sa.Column("tier_at_run", sa.String(length=20), nullable=False, server_default="free")
        )
        batch_op.add_column(sa.Column("paused_at_stage", sa.String(length=50), nullable=True))

    with op.batch_alter_table("pipeline_stage_logs") as batch_op:
        pass


def downgrade() -> None:
    with op.batch_alter_table("pipeline_runs") as batch_op:
        batch_op.drop_column("paused_at_stage")
        batch_op.drop_column("tier_at_run")

    op.drop_table("stage_reviews")
    op.drop_table("llm_configs")
