"""ADR-417 D4 — `pipeline_runs.cancelled_from_status`: o estado do run no instante terminal.

Existe porque a 1ª redação do D4 propunha DERIVAR "foi descartado?" de
`paused_at_stage`, e a medição refutou: ninguém nunca zera esse campo — o único
write é a pausa, e `_flip_run_to_resuming` o preserva de propósito (A40.l27, "a
única cópia durável do ponto de retomada"). Um campo cuja função declarada é
sobreviver ao avanço do run não pode discriminar QUANDO ele terminou.

`String(20)`, não `Enum(...)`: um segundo tipo enum nativo no Postgres traria o
`ALTER TYPE ... ADD VALUE` cujo custo o D3 já recusa. Forma precedente:
`tier_at_run` (String(20)), `failure_reason` (String(50)).

SEM backfill. Rows `cancelled` legadas ficam NULL, e NULL significa DESCONHECIDO —
nunca "interrompido". Inferir o valor delas a partir de `paused_at_stage` seria
commitar a derivação refutada dentro de uma migração, onde deixa de ser reversível.

Revision ID: adr417cfs
Revises: adr414flip
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "adr417cfs"
down_revision: Union[str, Sequence[str], None] = "adr414flip"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("pipeline_runs") as batch:
        batch.add_column(sa.Column("cancelled_from_status", sa.String(20), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("pipeline_runs") as batch:
        batch.drop_column("cancelled_from_status")
