"""LGPD self-service — data_export_requests + users.deletion_requested_at.

Revision ID: c3d4e5f6a7b8
Revises: b7c8d9e0f1a2
Create Date: 2026-05-04

Cobre LGPD Art. 18:
  V — portabilidade  →  data_export_requests (fila assíncrona)
  VI — eliminação    →  users.deletion_requested_at (soft-delete com grace
                        de 30 dias; cron finaliza hard-delete)

Sem PII no schema. Conteúdo do export vive em
`storage/lgpd_exports/<request_id>.tar.gz`, fora do DB.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, None] = "b7c8d9e0f1a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(
            sa.Column("deletion_requested_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch_op.create_index(
            "ix_users_deletion_requested_at",
            ["deletion_requested_at"],
            unique=False,
        )

    op.create_table(
        "data_export_requests",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(length=36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=16),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("download_token", sa.String(length=96), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("file_path", sa.String(length=512), nullable=True),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("download_token", name="uq_data_export_requests_token"),
    )
    op.create_index(
        "ix_data_export_requests_user_id",
        "data_export_requests",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_data_export_requests_status",
        "data_export_requests",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_data_export_requests_expires_at",
        "data_export_requests",
        ["expires_at"],
        unique=False,
    )
    op.create_index(
        "ix_data_export_requests_created_at",
        "data_export_requests",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_data_export_requests_created_at", table_name="data_export_requests")
    op.drop_index("ix_data_export_requests_expires_at", table_name="data_export_requests")
    op.drop_index("ix_data_export_requests_status", table_name="data_export_requests")
    op.drop_index("ix_data_export_requests_user_id", table_name="data_export_requests")
    op.drop_table("data_export_requests")
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_index("ix_users_deletion_requested_at")
        batch_op.drop_column("deletion_requested_at")
