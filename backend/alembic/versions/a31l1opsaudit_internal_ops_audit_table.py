"""A31.l1 — tabela internal_ops_audit (ADR-309, débito 7B.5).

Revision ID: a31l1opsaudit
Revises: a17l4itausa
Create Date: 2026-07-07

Audit de mutação de operador migra de logs/internal_ops_audit.log (JSONL)
para tabela — mesma transação da operação (ADR-309 D2). Tabela nova sem FK
(operador não é user, ADR-116); retenção indefinida, nenhum purge job toca
(ADR-309 D5). Em Postgres com role de app configurado (env
MATHOMS_DB_APP_ROLE), aplica REVOKE UPDATE/DELETE — imutabilidade real
(ADR-309 D4); sem o env, o passo fica no runbook de deploy. Linha
meta-audit action=audit.migration marca o corte do sink (sem backfill —
ADR-309 D6). Downgrade descarta o audit acumulado (destrutivo por design
pós-cutover; seguro na janela de deploy).
"""

import os
from datetime import datetime, timezone
from typing import Sequence, Union
from uuid import uuid4

import sqlalchemy as sa
from alembic import op

revision: str = "a31l1opsaudit"
down_revision: Union[str, Sequence[str], None] = "a17l4itausa"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "internal_ops_audit",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("actor", sa.String(100), nullable=False),
        sa.Column("target_type", sa.String(64), nullable=True),
        sa.Column("target_id", sa.String(255), nullable=True),
        sa.Column("result", sa.String(16), nullable=False, server_default="ok"),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_internal_ops_audit_created", "internal_ops_audit", ["created_at"])
    _revoke_mutations_if_postgres()
    _mark_cutover()


def _revoke_mutations_if_postgres() -> None:
    role = os.environ.get("MATHOMS_DB_APP_ROLE", "").strip()
    if op.get_bind().dialect.name != "postgresql" or not role:
        return
    op.execute(sa.text(f'REVOKE UPDATE, DELETE ON internal_ops_audit FROM "{role}"'))
    op.execute(sa.text(f'GRANT INSERT, SELECT ON internal_ops_audit TO "{role}"'))


def _mark_cutover() -> None:
    op.execute(
        sa.table(
            "internal_ops_audit",
            sa.column("id", sa.String),
            sa.column("action", sa.String),
            sa.column("actor", sa.String),
            sa.column("result", sa.String),
            sa.column("created_at", sa.DateTime(timezone=True)),
        )
        .insert()
        .values(
            id=str(uuid4()),
            action="audit.migration",
            actor="alembic:a31l1opsaudit",
            result="ok",
            created_at=datetime.now(timezone.utc),
        )
    )


def downgrade() -> None:
    op.drop_index("ix_internal_ops_audit_created", table_name="internal_ops_audit")
    op.drop_table("internal_ops_audit")
