"""Piso do IRPFM na row fiscal — detector de vinculação (A40.l64 PR4).

O produto não precisa do IRPFM ao centavo para NÃO errar o sinal. Precisa saber se
o mínimo pode vincular: acima do piso, o IR devido pela tabela é abatido do mínimo,
e a economia do PGBL tende a zero. Abaixo, o mínimo certamente não vincula.

O piso vive na ROW pelo mesmo motivo do redutor ([[ADR-414]] D3): a vigência vem do
DADO. `NULL`/0 = ano sem IRPFM, e é assim que AC <= 2025 fica de fora sem
`if year >= 2026` em lugar nenhum.

Revision ID: adr414irpfm
Revises: adr414redutor
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import context, op

revision: str = "adr414irpfm"
down_revision: Union[str, None] = "adr414redutor"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

#: Art. 16-A da Lei 9.250/1995 (inserido pela Lei 15.270/2025): a alíquota do
#: mínimo começa em R$ 600 mil de renda total e escalona até 10% em R$ 1,2M.
_LIMIAR_2026_CENTS = 60_000_000


def upgrade() -> None:
    if context.is_offline_mode():
        op.add_column(
            "fiscal_parameters", sa.Column("irpfm_limiar_brl_cents", sa.Integer(), nullable=True)
        )
        return
    with op.batch_alter_table("fiscal_parameters") as batch:
        batch.add_column(sa.Column("irpfm_limiar_brl_cents", sa.Integer(), nullable=True))
    op.get_bind().execute(
        sa.text("UPDATE fiscal_parameters SET irpfm_limiar_brl_cents = :v WHERE year >= 2026"),
        {"v": _LIMIAR_2026_CENTS},
    )


def downgrade() -> None:
    with op.batch_alter_table("fiscal_parameters") as batch:
        batch.drop_column("irpfm_limiar_brl_cents")
