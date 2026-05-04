"""post-review: workspaces.monthly_llm_budget_usd + tabela llm_call_log.

Revision ID: a5b6c7d8e9f0
Revises: z4a5b6c7d8e9
Create Date: 2026-05-04

Endereça oportunidade 0.3 do post-review: BYOK premium gerava custo
invisível em telemetria; sem cap por workspace, bug em retry pode
multiplicar conta sem alerta.

Mudanças schema:
- ``workspaces.monthly_llm_budget_usd`` Numeric(10,2) NOT NULL default 5.00.
  Default conservador (free tier); Premium customiza via UI admin.
- Nova tabela ``llm_call_log``: 1 linha por chamada LLM agregada por
  (workspace_id, stage, model_name) com tokens/custo/duração/timestamp.
  Custo em Numeric(12,6) — dinheiro nunca é float em DB (ADR-090 mirror).
- 2 índices compostos para suportar agregações tipo
  "spend_in_period(workspace_id, since)" sem table scan.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a5b6c7d8e9f0"
down_revision: Union[str, Sequence[str], None] = "z4a5b6c7d8e9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Coluna nova em workspaces — server_default para registros existentes.
    with op.batch_alter_table("workspaces") as batch:
        batch.add_column(
            sa.Column(
                "monthly_llm_budget_usd",
                sa.Numeric(10, 2),
                nullable=False,
                server_default="5.00",
            )
        )

    op.create_table(
        "llm_call_log",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.String(36),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("stage", sa.String(64), nullable=False),
        sa.Column("model_name", sa.String(120), nullable=False),
        sa.Column("prompt_version", sa.String(40), nullable=True),
        sa.Column("tokens_in", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tokens_out", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "cost_usd",
            sa.Numeric(12, 6),
            nullable=False,
            server_default="0.000000",
        ),
        sa.Column("cost_known", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("duration_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("pipeline_run_id", sa.String(36), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_llm_call_log_workspace_id", "llm_call_log", ["workspace_id"])
    op.create_index("ix_llm_call_log_pipeline_run_id", "llm_call_log", ["pipeline_run_id"])
    op.create_index("ix_llm_call_log_created_at", "llm_call_log", ["created_at"])
    op.create_index("ix_llm_call_log_ws_created", "llm_call_log", ["workspace_id", "created_at"])
    op.create_index(
        "ix_llm_call_log_ws_model_created",
        "llm_call_log",
        ["workspace_id", "model_name", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_llm_call_log_ws_model_created", table_name="llm_call_log")
    op.drop_index("ix_llm_call_log_ws_created", table_name="llm_call_log")
    op.drop_index("ix_llm_call_log_created_at", table_name="llm_call_log")
    op.drop_index("ix_llm_call_log_pipeline_run_id", table_name="llm_call_log")
    op.drop_index("ix_llm_call_log_workspace_id", table_name="llm_call_log")
    op.drop_table("llm_call_log")
    with op.batch_alter_table("workspaces") as batch:
        batch.drop_column("monthly_llm_budget_usd")
