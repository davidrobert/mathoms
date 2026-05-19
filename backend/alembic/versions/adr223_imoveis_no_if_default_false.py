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
from alembic import op

revision: str = "adr223defaultfalse"
down_revision: Union[str, None] = "adr224assetcatalog"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("workspaces", schema=None) as batch_op:
        batch_op.alter_column(
            "imoveis_no_if",
            existing_type=sa.Boolean(),
            existing_nullable=False,
            server_default=sa.text("0"),
        )


def downgrade() -> None:
    with op.batch_alter_table("workspaces", schema=None) as batch_op:
        batch_op.alter_column(
            "imoveis_no_if",
            existing_type=sa.Boolean(),
            existing_nullable=False,
            server_default=sa.text("1"),
        )
