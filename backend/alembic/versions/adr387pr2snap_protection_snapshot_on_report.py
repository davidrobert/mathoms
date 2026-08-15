"""ADR-387 PR2: snapshot de proteção no Report + hash versionado na publicação.

Revision ID: adr387pr2snap
Revises: adr387pr1src
Create Date: 2026-08-15
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import MetaData, Table

revision: str = "adr387pr2snap"
down_revision: Union[str, Sequence[str], None] = "adr387pr1src"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _publications_columns() -> tuple:
    return (
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("workspace_id", sa.String(36), nullable=False),
        sa.Column("period_yyyymm", sa.String(6), nullable=False),
        sa.Column("artifact_id", sa.Integer(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_by", sa.String(64), nullable=False),
        sa.Column("immutable_hash", sa.String(64), nullable=False),
        sa.Column("unpublished_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["artifact_id"], ["pipeline_artifacts.id"], ondelete="RESTRICT"),
        sa.CheckConstraint("length(period_yyyymm) = 6", name="ck_report_publications_period_len"),
    )


def _publications_pre() -> Table:
    return Table("report_publications", MetaData(), *_publications_columns())


def _publications_post() -> Table:
    return Table(
        "report_publications",
        MetaData(),
        *_publications_columns(),
        sa.Column("report_id", sa.String(36)),
        sa.Column("hash_version", sa.String(16), nullable=False, server_default="e5-v1"),
    )


def _add_publication_columns(batch_op) -> None:
    batch_op.add_column(sa.Column("report_id", sa.String(36)))
    batch_op.add_column(
        sa.Column("hash_version", sa.String(16), nullable=False, server_default="e5-v1")
    )
    batch_op.create_foreign_key(
        "fk_report_publications_report_id",
        "reports",
        ["report_id"],
        ["id"],
        ondelete="SET NULL",
    )
    batch_op.create_check_constraint(
        "chk_report_publication_hash_version",
        "hash_version IN ('e5-v1','report-v2')",
    )


def upgrade() -> None:
    op.add_column("reports", sa.Column("protection_snapshot_json", sa.JSON(), nullable=True))
    with op.batch_alter_table("report_publications", copy_from=_publications_pre()) as batch_op:
        _add_publication_columns(batch_op)
    op.create_index(
        "ix_report_publications_report_id",
        "report_publications",
        ["report_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_report_publications_report_id", table_name="report_publications")
    with op.batch_alter_table("report_publications", copy_from=_publications_post()) as batch_op:
        batch_op.drop_column("hash_version")
        batch_op.drop_column("report_id")
    op.drop_column("reports", "protection_snapshot_json")
