"""ADR-411 · A40.l81 — `review_reasons.locator`: a posição da razão no artefato.

O sink passa a rodar em todo desfecho de stage, e a colheita caminha o artefato
inteiro (topo + coleções aninhadas). Sem a posição, duas razões de códigos iguais
vindas de lugares diferentes colapsariam numa row cujo ponteiro o operador não
reencontra — o defeito de RV8-19.

Expand puro: coluna NOT NULL com `server_default=""`. Rows históricas recebem
vazio, que o leitor mostra como "caminho desconhecido". Vazio e não NULL porque a
chave de consolidação compara por igualdade e `NULL = NULL` é falso em SQL —
locator nulo quebraria a idempotência do redelivery do Celery (`acks_late`).

Revision ID: adr411locator
Revises: adr389tabelas
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "adr411locator"
down_revision: Union[str, None] = "adr389tabelas"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "review_reasons",
        sa.Column("locator", sa.String(length=255), nullable=False, server_default=""),
    )


def downgrade() -> None:
    op.drop_column("review_reasons", "locator")
