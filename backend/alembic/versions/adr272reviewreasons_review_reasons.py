"""adr-272 review_reasons (Revision: adr272reviewreasons, Revises: adr269tsdedup, Create Date: 2026-05-30). Projeção consultável da razão de needs_review: tabela 1:N por pipeline_run com índice composto (workspace_id, pipeline_run_id, code) para a query-mãe. Sem backfill — populada pela Fase 2."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "adr272reviewreasons"
down_revision: Union[str, None] = "adr269tsdedup"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "review_reasons",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("pipeline_run_id", sa.String(length=36), nullable=False),
        sa.Column("stage", sa.String(length=50), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("artifact_key", sa.String(length=255), nullable=False),
        sa.Column("document_id", sa.String(length=36), nullable=True),
        sa.Column("offending_value", sa.Text(), nullable=False),
        sa.Column("expected", sa.Text(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("occurrence_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["pipeline_run_id"], ["pipeline_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("review_reasons", schema=None) as batch_op:
        batch_op.create_index("ix_review_reasons_workspace_id", ["workspace_id"], unique=False)
        batch_op.create_index(
            "ix_review_reasons_pipeline_run_id", ["pipeline_run_id"], unique=False
        )
        batch_op.create_index(
            "ix_review_reasons_ws_run_code",
            ["workspace_id", "pipeline_run_id", "code"],
            unique=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("review_reasons", schema=None) as batch_op:
        batch_op.drop_index("ix_review_reasons_ws_run_code")
        batch_op.drop_index("ix_review_reasons_pipeline_run_id")
        batch_op.drop_index("ix_review_reasons_workspace_id")
    op.drop_table("review_reasons")
