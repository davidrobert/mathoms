"""ADR-162 (Onda 8 #3) — derived_from_decision_id em tasks.

Revision ID: f1a2b3c4d5e6
Revises: e0f1a2b3c4d5
Create Date: 2026-05-04

Adiciona coluna ``derived_from_decision_id`` (String(36) FK→decisions.id,
nullable, ON DELETE SET NULL) na tabela ``tasks``. Sinaliza Tasks
geradas a partir do botão "Gerar tarefas" no DecisionCard, habilitando
métrica "X% das tarefas vêm de decisão" (sinal de aderência
metodológica) e auditoria reversa Decision → Tasks derivadas.

Tasks pré-migration ficam com NULL — comportamento normal (criadas
via manual/seed/llm_suggestion, sem origem em Decision).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "e0f1a2b3c4d5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("tasks") as batch:
        batch.add_column(sa.Column("derived_from_decision_id", sa.String(36), nullable=True))
        batch.create_foreign_key(
            "fk_tasks_derived_from_decision",
            "decisions",
            ["derived_from_decision_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch.create_index(
            "ix_tasks_derived_from_decision_id",
            ["derived_from_decision_id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("tasks") as batch:
        batch.drop_index("ix_tasks_derived_from_decision_id")
        batch.drop_constraint("fk_tasks_derived_from_decision", type_="foreignkey")
        batch.drop_column("derived_from_decision_id")
