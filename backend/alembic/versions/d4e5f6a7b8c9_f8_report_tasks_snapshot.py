"""f8_report_tasks_snapshot

Revision ID: d4e5f6a7b8c9
Revises: c2d3e4f5a6b7
Create Date: 2026-04-15

ADR-074 §F8.3 — adiciona `Report.tasks_snapshot_json` (JSON) para
preservar o estado do backlog no momento da geração do relatório.
Isso permite:

  - Relatório vira snapshot imutável (mesmo que backlog mude, o que
    vemos no report de 15/abr é o estado de 15/abr).
  - Remove dependência do E6 de parsear `tarefas.md` no momento de
    renderizar o HTML legado.

Nullable para backward-compat com relatórios pré-F8.3.
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "c2d3e4f5a6b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("reports", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("tasks_snapshot_json", sa.JSON(), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("reports", schema=None) as batch_op:
        batch_op.drop_column("tasks_snapshot_json")
