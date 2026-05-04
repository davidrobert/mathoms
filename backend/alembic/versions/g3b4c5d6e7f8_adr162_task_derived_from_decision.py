"""ADR-162 (Onda 8 #3) — derived_from_decision_id em tasks.

Revision ID: g3b4c5d6e7f8
Revises: e0f1a2b3c4d5
Create Date: 2026-05-04

Adiciona coluna ``derived_from_decision_id`` (String(36) FK→decisions.id,
nullable, ON DELETE SET NULL) na tabela ``tasks``. Sinaliza Tasks
geradas a partir do botão "Gerar tarefas" no DecisionCard, habilitando
métrica "X% das tarefas vêm de decisão" (sinal de aderência
metodológica) e auditoria reversa Decision → Tasks derivadas.

Tasks pré-migration ficam com NULL — comportamento normal (criadas
via manual/seed/llm_suggestion, sem origem em Decision).

Usa ``op.batch_alter_table(copy_from=...)`` com snapshot completo da
tabela ``tasks`` (pós-ADR-154) — exigido para SQLite + offline SQL
generation (test_offline_sql_generation_works).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "g3b4c5d6e7f8"
down_revision: Union[str, Sequence[str], None] = "e0f1a2b3c4d5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_FK_NAME = "fk_tasks_derived_from_decision"
_INDEX_NAME = "ix_tasks_derived_from_decision_id"


def _tasks_columns_pre() -> list[sa.Column]:
    """Snapshot das colunas de ``tasks`` antes desta migration (pós-ADR-154 M1)."""
    return [
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("workspace_id", sa.String(36), nullable=False),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(64), nullable=False),
        sa.Column("priority", sa.String(1), nullable=False),
        sa.Column("deadline_kind", sa.String(32), nullable=False),
        sa.Column("deadline_date", sa.Date(), nullable=True),
        sa.Column("deadline_label", sa.String(128), nullable=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("status_reason", sa.Text(), nullable=True),
        sa.Column("ref", sa.String(255), nullable=True),
        sa.Column("parent_task_id", sa.String(36), nullable=True),
        sa.Column("related_transaction_id", sa.String(36), nullable=True),
        sa.Column("related_goal_id", sa.String(36), nullable=True),
        sa.Column("assigned_to", sa.String(36), nullable=True),
        sa.Column("created_from", sa.String(32), nullable=False),
        sa.Column("source_suggestion_id", sa.String(36), nullable=True),
        sa.Column("board_column", sa.String(32), nullable=True),
        sa.Column("board_order", sa.Integer(), nullable=True),
        sa.Column("origin_report_id", sa.String(36), nullable=True),
        sa.Column("urgency", sa.String(8), nullable=True),
        sa.Column("is_board_only", sa.Boolean(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    ]


def _tasks_table_pre() -> sa.Table:
    md = sa.MetaData()
    return sa.Table(
        "tasks",
        md,
        *_tasks_columns_pre(),
        sa.UniqueConstraint("workspace_id", "number", name="uq_task_ws_number"),
    )


def upgrade() -> None:
    with op.batch_alter_table("tasks", copy_from=_tasks_table_pre()) as batch:
        batch.add_column(
            sa.Column(
                "derived_from_decision_id",
                sa.String(length=36),
                sa.ForeignKey("decisions.id", name=_FK_NAME, ondelete="SET NULL"),
                nullable=True,
            )
        )
        batch.create_index(_INDEX_NAME, ["derived_from_decision_id"])


def downgrade() -> None:
    with op.batch_alter_table("tasks") as batch:
        batch.drop_index(_INDEX_NAME)
        batch.drop_constraint(_FK_NAME, type_="foreignkey")
        batch.drop_column("derived_from_decision_id")
