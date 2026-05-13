"""ADR-199 / ADR-204 / ADR-208 — planner_review_metadata + pipeline_run_costs (PR-3). Revision ID: e3d4e5f6a7b8 / Revises: d2c3d4e5f6a7 / Create Date: 2026-05-13."""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e3d4e5f6a7b8"
down_revision: Union[str, None] = "d2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_PR_INDEXES = (
    ("ix_planner_review_metadata_workspace_id", ["workspace_id"]),
    ("ix_planner_review_metadata_pipeline_run_id", ["pipeline_run_id"]),
    ("ix_planner_review_metadata_pipeline_artifact_id", ["pipeline_artifact_id"]),
    ("ix_planner_review_metadata_e5_artifact_id", ["e5_artifact_id"]),
    ("ix_planner_review_metadata_status", ["status"]),
    ("ix_planner_review_metadata_supersedes_id", ["supersedes_id"]),
    ("ix_planner_review_metadata_superseded_by_id", ["superseded_by_id"]),
    ("ix_planner_review_metadata_created_at", ["created_at"]),
    ("ix_planner_review_workspace_status", ["workspace_id", "status"]),
)

_COST_INDEXES = (
    ("ix_pipeline_run_costs_pipeline_run_id", ["pipeline_run_id"]),
    ("ix_pipeline_run_costs_workspace_id", ["workspace_id"]),
    ("ix_pipeline_run_costs_stage", ["stage", "created_at"]),
    ("ix_pipeline_run_costs_workspace_date", ["workspace_id", "created_at"]),
)


def upgrade() -> None:
    _create_planner_review_table()
    _create_indexes("planner_review_metadata", _PR_INDEXES)
    _create_pipeline_run_costs_table()
    _create_indexes("pipeline_run_costs", _COST_INDEXES)


def downgrade() -> None:
    _drop_indexes("pipeline_run_costs", _COST_INDEXES)
    op.drop_table("pipeline_run_costs")
    _drop_indexes("planner_review_metadata", _PR_INDEXES)
    op.drop_table("planner_review_metadata")


def _planner_review_identity_columns() -> tuple:
    return (
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("pipeline_run_id", sa.String(length=36), nullable=False),
        sa.Column("pipeline_artifact_id", sa.Integer(), nullable=False),
        sa.Column("e5_artifact_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("supersedes_id", sa.String(length=36), nullable=True),
        sa.Column("superseded_by_id", sa.String(length=36), nullable=True),
    )


def _planner_review_audit_columns() -> tuple:
    return (
        sa.Column("persona_hash", sa.String(length=64), nullable=False),
        sa.Column("manifest_version", sa.String(length=20), nullable=False),
        sa.Column("schema_version", sa.String(length=20), nullable=False),
        sa.Column("model_id", sa.String(length=100), nullable=False),
        sa.Column("immutable_hash", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("superseded_at", sa.DateTime(timezone=True), nullable=True),
    )


def _planner_review_telemetry_columns() -> tuple:
    return (
        sa.Column("tier_at_generation", sa.String(length=20), nullable=False),
        sa.Column("items_shown_count", sa.Integer(), nullable=False),
        sa.Column("items_gated_count", sa.Integer(), nullable=False),
        sa.Column("cost_usd_cents", sa.BigInteger(), nullable=False),
        sa.Column("tokens_in", sa.Integer(), nullable=False),
        sa.Column("tokens_out", sa.Integer(), nullable=False),
        sa.Column("tool_iterations", sa.Integer(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
    )


def _planner_review_constraints() -> tuple:
    return (
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["pipeline_run_id"], ["pipeline_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["pipeline_artifact_id"], ["pipeline_artifacts.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["e5_artifact_id"], ["pipeline_artifacts.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["supersedes_id"], ["planner_review_metadata.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "workspace_id", "pipeline_run_id", name="uq_planner_review_workspace_run"
        ),
        sa.UniqueConstraint("pipeline_artifact_id", name="uq_planner_review_artifact"),
    )


def _create_planner_review_table() -> None:
    """Metadata projection sobre pipeline_artifacts (ADR-199 §D3)."""
    op.create_table(
        "planner_review_metadata",
        *_planner_review_identity_columns(),
        *_planner_review_audit_columns(),
        *_planner_review_telemetry_columns(),
        *_planner_review_constraints(),
    )


def _pipeline_run_costs_columns() -> tuple:
    return (
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("pipeline_run_id", sa.String(length=36), nullable=False),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("stage", sa.String(length=50), nullable=False),
        sa.Column("model_id", sa.String(length=100), nullable=False),
        sa.Column("tokens_in", sa.Integer(), nullable=False),
        sa.Column("tokens_out", sa.Integer(), nullable=False),
        sa.Column("cost_usd_cents", sa.BigInteger(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("tool_iterations", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def _create_pipeline_run_costs_table() -> None:
    """FinOps por stage execution — PR-3 do plano canônico."""
    op.create_table(
        "pipeline_run_costs",
        *_pipeline_run_costs_columns(),
        sa.ForeignKeyConstraint(["pipeline_run_id"], ["pipeline_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def _create_indexes(table_name: str, indexes: tuple) -> None:
    with op.batch_alter_table(table_name) as batch_op:
        for name, cols in indexes:
            batch_op.create_index(name, cols, unique=False)


def _drop_indexes(table_name: str, indexes: tuple) -> None:
    with op.batch_alter_table(table_name) as batch_op:
        for name, _cols in reversed(indexes):
            batch_op.drop_index(name)
