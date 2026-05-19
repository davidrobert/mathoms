"""adr-223 — flip default `workspaces.imoveis_no_if` para false (FU-1 backend).

Revision ID: adr223defaultfalse
Revises: adr224assetcatalog
Create Date: 2026-05-19

ADR-223 §1: muda apenas o DDL default da coluna. Rows existentes
**não** são tocadas — flip retroativo silencioso quebra confiança.
Workspaces criados após esta migration nascem com `imoveis_no_if=false`
+ `set_at=NULL`; opt-in para `true` via UX banner (A13).
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import context, op

revision: str = "adr223defaultfalse"
down_revision: Union[str, None] = "adr224assetcatalog"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _alter_default(default_text: str) -> None:
    """Alter `workspaces.imoveis_no_if` server_default — dialect-aware.

    - Offline mode (`alembic upgrade --sql`): emite comentário (batch_alter_table
      em SQLite requer reflection que falha sem DB live).
    - SQLite online: batch_alter_table (rebuild necessário; SQLite não tem
      ``ALTER COLUMN``).
    - Postgres/outros: ``alter_column`` direto.
    """
    if context.is_offline_mode():
        op.execute(
            f"-- ADR-223: workspaces.imoveis_no_if server_default → {default_text} "
            "(Postgres ALTER COLUMN ... SET DEFAULT; SQLite via batch rebuild online)"
        )
        return
    bind = op.get_bind()
    if bind is not None and bind.dialect.name == "sqlite":
        with op.batch_alter_table("workspaces", schema=None) as batch_op:
            batch_op.alter_column(
                "imoveis_no_if",
                existing_type=sa.Boolean(),
                existing_nullable=False,
                server_default=sa.text(default_text),
            )
        return
    op.alter_column(
        "workspaces",
        "imoveis_no_if",
        existing_type=sa.Boolean(),
        existing_nullable=False,
        server_default=sa.text(default_text),
    )


def upgrade() -> None:
    _alter_default("0")


def downgrade() -> None:
    _alter_default("1")
