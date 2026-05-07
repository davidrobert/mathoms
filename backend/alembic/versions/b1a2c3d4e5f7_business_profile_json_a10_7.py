"""ADR-A10.7 — adiciona Workspace.business_profile_json (JSON livre).

Revision ID: b1a2c3d4e5f7
Revises: 96aa57403806
Create Date: 2026-05-07

Sprint A10.7 — `tributario` (chave do legado `config/goals.json` com
`{contador, regime, holding_prazo}`) sai da bag `PLANNING_CONTEXT` e vira
campo JSON livre em `Workspace`. Estrutura simples, cliente-PJ-específica,
não merece aggregate dedicado — `BusinessProfile` (Pydantic) valida shape
no boundary HTTP.

Migration **non-breaking** — coluna nullable; workspaces existentes ficam
com `NULL` até o consultor preencher via PATCH.

Schema delta:
    workspaces
        + business_profile_json JSON NULL
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b1a2c3d4e5f7"
down_revision: Union[str, None] = "96aa57403806"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("workspaces", schema=None) as batch_op:
        batch_op.add_column(sa.Column("business_profile_json", sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("workspaces", schema=None) as batch_op:
        batch_op.drop_column("business_profile_json")
