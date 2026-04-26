"""adr-130 transfer_configs (transferencias_internas → DB)

Revision ID: w1x2y3z4a5b6
Revises: v0w1x2y3z4a5
Create Date: 2026-04-25

ADR-133: extrai o bloco ``transferencias_internas`` de
``config/family_members.json`` para a tabela ``transfer_configs``
(workspace-scoped). Consumidor primário: ``InternalTransferDetector``
no E4 e no use case ``list_consumo_pontuais``.

Rationale: antes desta migration, esses recipients/patterns eram
**globais para todos os workspaces** (só viviam no repo). Agora cada
workspace pode customizar via ``PUT /workspaces/{id}/config/transfer``
(família, conjuge, contas próprias variam por usuário).

Backfill: a migration cria a tabela vazia. Workspaces sem row caem no
default global de ``config/family_members.json::transferencias_internas``
via ``ConfigDefaultsLoader`` — sem mudança de comportamento até o
usuário editar.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "w1x2y3z4a5b6"
down_revision: Union[str, None] = "v0w1x2y3z4a5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "transfer_configs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("config_json", sa.JSON(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("transfer_configs", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_transfer_configs_workspace_id"), ["workspace_id"], unique=True
        )


def downgrade() -> None:
    with op.batch_alter_table("transfer_configs", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_transfer_configs_workspace_id"))
    op.drop_table("transfer_configs")
