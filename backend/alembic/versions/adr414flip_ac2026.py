"""AC2026 vira `regime_completo: true` — os componentes existem (A40.l64 §Critério 3).

A row nasceu `false` em 2026-08-16 declarando `["redutor_lei_15270", "irpfm"]`
ausentes. Os dois deixaram de estar: o redutor tem contrato tipado e compõe na
diferencial ([[ADR-414]] D4), e o IRPFM tem detector que **suprime** acima do piso
em vez de prescrever com sinal invertido (D5). Manter `false` passou a ser a row
afirmando o que a medição refuta.

O que torna o flip SEGURO é o que ele NÃO liga: com 2+ declarações no ano-base a
prescrição continua retida, agora por `base_familiar_nao_particionada`. A base do
card ainda soma as declarações e a progressividade não é aditiva, então ali o
número sairia superestimado — e publicar economia alta é a mis-sale que a lane
existe para impedir. Publica-se onde está certo; recusa-se onde se sabe enviesado.

Revision ID: adr414flip
Revises: adr414irpfm
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import context, op

revision: str = "adr414flip"
down_revision: Union[str, None] = "adr414irpfm"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

#: Consumido pelo substrato de golden para NÃO divergir da produção — a fixture
#: derivava só da migration ADR-389, onde AC2026 é `false`, e ficaria afirmando uma
#: retenção que a produção deixou de fazer. É LIMIAR, não conjunto: espelha o
#: `WHERE year >= 2026` do UPDATE, senão a fixture e o SQL discordam em 2027.
ANO_INICIAL_REGIME_COMPLETO = 2026


def upgrade() -> None:
    if context.is_offline_mode():
        op.execute(
            "-- ADR-414: UPDATE fiscal_parameters SET regime_completo=true, "
            "componentes_ausentes='[]' WHERE year >= 2026"
        )
        return
    # `true`/`false`, não 1/0: SQLite é frouxo e aceita o inteiro, Postgres levanta
    # DatatypeMismatchError — produção é PG e a cadeia parava aqui.
    op.get_bind().execute(
        sa.text(
            "UPDATE fiscal_parameters SET regime_completo = true, componentes_ausentes = '[]' "
            "WHERE year >= 2026"
        )
    )


def downgrade() -> None:
    op.get_bind().execute(
        sa.text(
            "UPDATE fiscal_parameters SET regime_completo = false, "
            'componentes_ausentes = \'["redutor_lei_15270", "irpfm"]\' WHERE year >= 2026'
        )
    )
