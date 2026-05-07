"""ADR-179 — Decision schema extension (impact_1y/10y, horizon, priority).

Revision ID: 96aa57403806
Revises: a4b5c6d7e8f9
Create Date: 2026-05-06

ADR-179 (Sprint A10.3): adiciona 4 colunas a ``decisions`` para suportar
quantificação de impacto (1y/10y), horizonte temporal e prioridade
manual do consultor — habilita lane A10.5 (Top5/Bubble como projeção).

Migration **non-breaking** — campos nullable; ``horizon`` com default
``'short_6_12m'`` permite registros existentes continuarem servíveis.
Backfill heurístico opcional via ``backend/app/scripts/backfill_decision_impact.py``.

Schema delta (ver ``backend/app/models/decision.py``):
    decisions
        + impact_1y_brl_cents BIGINT NULL
        + impact_10y_brl_cents BIGINT NULL
        + horizon VARCHAR(16) NOT NULL DEFAULT 'short_6_12m'
        + priority SMALLINT NULL
        + INDEX ix_decisions_ws_horizon (workspace_id, horizon)

Money sempre em ``BIGINT`` cents (ADR-090). ``horizon`` é texto livre
validado no service layer (frozenset em ``models/decision.py``).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "96aa57403806"
down_revision: Union[str, None] = (
    "a4b5c6d7e8f9"  # ADR-178 (A10.4) — encadeado durante rebase Wave 2
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("decisions", schema=None) as batch_op:
        batch_op.add_column(sa.Column("impact_1y_brl_cents", sa.BigInteger(), nullable=True))
        batch_op.add_column(sa.Column("impact_10y_brl_cents", sa.BigInteger(), nullable=True))
        batch_op.add_column(
            sa.Column(
                "horizon",
                sa.String(length=16),
                nullable=False,
                server_default="short_6_12m",
            )
        )
        batch_op.add_column(sa.Column("priority", sa.SmallInteger(), nullable=True))
        batch_op.create_index(
            "ix_decisions_ws_horizon",
            ["workspace_id", "horizon"],
            unique=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("decisions", schema=None) as batch_op:
        batch_op.drop_index("ix_decisions_ws_horizon")
        batch_op.drop_column("priority")
        batch_op.drop_column("horizon")
        batch_op.drop_column("impact_10y_brl_cents")
        batch_op.drop_column("impact_1y_brl_cents")
