"""A33.l5 — tabela llm_drift_check (ADR-307 F2).

Revision ID: a33l5driftchk
Revises: a31l1opsaudit
Create Date: 2026-07-07

Resultado estrutural do drift nightly do extract_with_llm, 1 row por
fixture por execução — pass/fail consultável independente de cache hit
(cache hit não grava LLMCallLog, ADR-307 D5). Sem FK de workspace: o
drift-check avalia contrato global de prompt/provider; custo da chamada
fica no llm_call_log via hooks ADR-173. Downgrade dropa a tabela
(telemetria derivada, reversível trivial).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a33l5driftchk"
down_revision: Union[str, Sequence[str], None] = "a31l1opsaudit"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "llm_drift_check",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("batch_id", sa.String(36), nullable=False),
        sa.Column("stage", sa.String(64), nullable=False),
        sa.Column("fixture_id", sa.String(80), nullable=False),
        sa.Column("prompt_version", sa.String(40), nullable=True),
        sa.Column("model_name", sa.String(120), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("failures", sa.JSON(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_llm_drift_check_batch_id", "llm_drift_check", ["batch_id"])
    op.create_index("ix_llm_drift_check_created_at", "llm_drift_check", ["created_at"])
    op.create_index("ix_llm_drift_check_stage_created", "llm_drift_check", ["stage", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_llm_drift_check_stage_created", table_name="llm_drift_check")
    op.drop_index("ix_llm_drift_check_created_at", table_name="llm_drift_check")
    op.drop_index("ix_llm_drift_check_batch_id", table_name="llm_drift_check")
    op.drop_table("llm_drift_check")
