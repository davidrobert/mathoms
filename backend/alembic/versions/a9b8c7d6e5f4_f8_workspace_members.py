"""f8_workspace_members

Revision ID: a9b8c7d6e5f4
Revises: f1a2b3c4d5e6
Create Date: 2026-04-15

ADR-072 — Multi-tenancy via WorkspaceMember.

Cria a tabela `workspace_members` (N:N user↔workspace com `role`) e faz
backfill de todos os workspaces existentes com um único membro `owner`
derivado de `workspaces.owner_id`. A partir desta migration, autorização
de acesso a workspace passa por `workspace_members`, não por
`workspaces.owner_id` (que vira metadado de "criador original").

A migration é idempotente: se executada duas vezes, não duplica backfill
(INSERT condicional em linhas que ainda não existem).
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a9b8c7d6e5f4"
down_revision: Union[str, None] = "f1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "workspace_members",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.String(length=36),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.String(length=36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "role",
            sa.String(length=32),
            nullable=False,
            server_default=sa.text("'member'"),
        ),
        sa.Column(
            "invited_by",
            sa.String(length=36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "joined_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("workspace_id", "user_id", name="uq_workspace_member"),
    )
    op.create_index(
        "ix_workspace_members_workspace_id",
        "workspace_members",
        ["workspace_id"],
    )
    op.create_index(
        "ix_workspace_members_user_id",
        "workspace_members",
        ["user_id"],
    )
    op.create_index(
        "ix_workspace_members_ws_user",
        "workspace_members",
        ["workspace_id", "user_id"],
    )

    # Backfill: para cada workspace existente, cria uma linha owner com
    # user_id = workspaces.owner_id. Idempotente via NOT EXISTS.
    # Usamos hex(randomblob(16)) para SQLite e gen_random_uuid() para PG
    # — ambos aceitos como string UUID. Como o driver async pode não ter
    # extensão pgcrypto garantida, geramos o id em Python durante o
    # backfill via loop explícito, que funciona em qualquer dialeto.
    #
    # Pula em offline mode (--sql): backfill data-driven não faz sentido
    # quando estamos só gerando script SQL preview. O DBA roda o backfill
    # manualmente após aplicar o DDL.
    if op.get_context().as_sql:
        return

    conn = op.get_bind()
    workspaces = conn.execute(
        sa.text(
            "SELECT id, owner_id, created_at FROM workspaces"
        )
    ).fetchall()
    import uuid

    for ws in workspaces:
        ws_id, owner_id, created_at = ws
        existing = conn.execute(
            sa.text(
                "SELECT 1 FROM workspace_members "
                "WHERE workspace_id = :ws AND user_id = :uid"
            ),
            {"ws": ws_id, "uid": owner_id},
        ).fetchone()
        if existing:
            continue
        conn.execute(
            sa.text(
                "INSERT INTO workspace_members "
                "(id, workspace_id, user_id, role, invited_by, joined_at) "
                "VALUES (:id, :ws, :uid, 'owner', NULL, :joined_at)"
            ),
            {
                "id": str(uuid.uuid4()),
                "ws": ws_id,
                "uid": owner_id,
                "joined_at": created_at,
            },
        )


def downgrade() -> None:
    op.drop_index("ix_workspace_members_ws_user", table_name="workspace_members")
    op.drop_index("ix_workspace_members_user_id", table_name="workspace_members")
    op.drop_index("ix_workspace_members_workspace_id", table_name="workspace_members")
    op.drop_table("workspace_members")
