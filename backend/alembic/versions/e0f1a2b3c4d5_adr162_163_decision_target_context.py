"""ADR-162 + ADR-163 — target_field/value/type + context_snapshot em decisions.

Revision ID: e0f1a2b3c4d5
Revises: d9e0f1a2b3c4
Create Date: 2026-05-04

Mudanças aditivas (todas nullable):

- ``target_field`` String(64): caminho dot-notation indicando qual campo
  de Goal a Decision atualiza ao virar Executada (ADR-162). Ex.:
  ``goal.if.trs_pct``, ``goal.aporte.meta_aporte_mensal_brl``.
- ``target_value`` String(128): valor decimal/string serializado.
- ``target_value_type`` String(8): ``pct`` | ``brl`` | ``int`` | ``str``.
- ``context_snapshot`` JSON: KPIs frozen do relatório-fonte da Suggestion
  no momento da aceitação (ADR-163). 5-7 campos: ``patrimonio_brl``,
  ``if_progress_pct``, ``trs_pct_when_decided``, ``report_id``,
  ``report_period``.

Decisions pré-migration ficam com NULL em todos — UI/projection degradam
graciosamente.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e0f1a2b3c4d5"
down_revision: Union[str, Sequence[str], None] = "d9e0f1a2b3c4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("decisions") as batch:
        batch.add_column(sa.Column("target_field", sa.String(64), nullable=True))
        batch.add_column(sa.Column("target_value", sa.String(128), nullable=True))
        batch.add_column(sa.Column("target_value_type", sa.String(8), nullable=True))
        batch.add_column(sa.Column("context_snapshot", sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("decisions") as batch:
        batch.drop_column("context_snapshot")
        batch.drop_column("target_value_type")
        batch.drop_column("target_value")
        batch.drop_column("target_field")
