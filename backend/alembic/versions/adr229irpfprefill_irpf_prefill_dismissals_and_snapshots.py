"""ADR-229: IRPF pre-fill — workspace_irpf_suggestion_dismissals + bank_accounts.irpf_snapshots.

Adiciona tabela de descartes persistentes de sugestões IRPF (com UNIQUE
``(workspace_id, irpf_year, institution_code, account_number_norm)`` para
idempotência) e coluna ``irpf_snapshots JSON NULL`` em ``bank_accounts``
para timeline anual de saldos declarados.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "adr229irpfprefill"
down_revision: Union[str, Sequence[str], None] = "b8c9d0e1f2a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "workspace_irpf_suggestion_dismissals",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.String(length=36),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("irpf_year", sa.Integer(), nullable=False),
        sa.Column("institution_code", sa.String(length=50), nullable=False),
        sa.Column("account_number_norm", sa.String(length=30), nullable=True),
        sa.Column("member_key", sa.String(length=50), nullable=True),
        sa.Column("dismissed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_by_user_id",
            sa.String(length=36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.UniqueConstraint(
            "workspace_id",
            "irpf_year",
            "institution_code",
            "account_number_norm",
            name="uq_workspace_irpf_dismissal",
        ),
    )

    with op.batch_alter_table("bank_accounts") as batch:
        batch.add_column(sa.Column("irpf_snapshots", sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("bank_accounts") as batch:
        batch.drop_column("irpf_snapshots")
    op.drop_table("workspace_irpf_suggestion_dismissals")
