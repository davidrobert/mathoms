"""adr-192 family_members.us_tax_status (T03)

Revision ID: d0e1f2a3b4c5
Revises: c9d0e1f2a3b4
Create Date: 2026-05-12

ADR-192 §D4 (Sprint A11.W5, S9-T03): introduz coluna ``us_tax_status`` em
``family_members`` para derivar ``ProtectionBundle.has_us_exposure`` a partir
de sinal estruturado por membro familiar. Códigos aceitos
(enforce a nível de aplicação):

    "none"                          ← default; sem exposição EUA
    "resident"                      ← US tax resident
    "former_resident_within_10y"    ← expatriação recente; ainda tributável
    "greencard_expiring"            ← green card em vias de perda
    "citizen"                       ← cidadão americano

Coluna nullable + default NULL para retrocompatibilidade — workspaces
existentes não exigem backfill. Calculator
``compliance_risk_us_person`` trata ``None`` como ``"none"``.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d0e1f2a3b4c5"
down_revision: Union[str, None] = "c9d0e1f2a3b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("family_members") as batch_op:
        batch_op.add_column(
            sa.Column("us_tax_status", sa.String(length=32), nullable=True, default=None)
        )


def downgrade() -> None:
    with op.batch_alter_table("family_members") as batch_op:
        batch_op.drop_column("us_tax_status")
