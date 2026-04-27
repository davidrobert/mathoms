"""adr-135 fiscal_parameters + market_rates (séries temporais globais)

Revision ID: x2adr135fp01
Revises: w1x2y3z4a5b6
Create Date: 2026-04-27

ADR-135: extrai ``config/parametros_fiscais.json`` e ``config/taxas.json``
para tabelas **globais** versionadas por data. Migração backwards-compat:
adiciona tabelas vazias; seed em ``data_migrations/seed_fiscal_2024_2026.py``
popula vigências para 2024/2025/2026 e cotações correntes USD/BRL e EUR/BRL.

Schema:
- ``fiscal_parameters``: vigência fina (effective_from/to) — selecionado
  pelo período do relatório, não data de geração.
- ``market_rates``: série de cotações por par + observed_at; "última conhecida
  até a data" para reproducibilidade histórica.

Money em ``BIGINT`` cents (PGBL/INSS) ou ``DECIMAL(20,10)`` (rate, alíquota)
[ADR-090]. Rationale completa em ``docs/DECISIONS.md#adr-135``.

A7.6 nota: revision ID renomeado de ``x2y3z4a5b6c7`` → ``x2adr135fp01``
porque colidia com o ID escolhido por A7.2a (decisions). Era pre-existing
bug que manteve dois alembic heads desde 2026-04-27 (ambas as lanes
mergearam no mesmo dia). Filename mantido para git blame; renomeação
apenas do ID interno + atualização do descendente ``y3z4a5b6c7d8``.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "x2adr135fp01"
down_revision: Union[str, None] = "w1x2y3z4a5b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "fiscal_parameters",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("ir_brackets", sa.JSON(), nullable=False),
        sa.Column("pgbl_limit_brl_cents", sa.BigInteger(), nullable=False),
        sa.Column("inss_ceiling_brl_cents", sa.BigInteger(), nullable=False),
        sa.Column("lucro_presumido_aliquota", sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("fiscal_parameters", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_fiscal_parameters_year"), ["year"], unique=False)
        batch_op.create_index(
            batch_op.f("ix_fiscal_parameters_effective_from"), ["effective_from"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_fiscal_parameters_effective_to"), ["effective_to"], unique=False
        )

    op.create_table(
        "market_rates",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("pair", sa.String(length=16), nullable=False),
        sa.Column("rate", sa.Numeric(precision=20, scale=10), nullable=False),
        sa.Column("observed_at", sa.Date(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("pair", "observed_at", name="uq_market_rates_pair_observed_at"),
    )
    with op.batch_alter_table("market_rates", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_market_rates_pair"), ["pair"], unique=False)
        batch_op.create_index(
            batch_op.f("ix_market_rates_observed_at"), ["observed_at"], unique=False
        )


def downgrade() -> None:
    with op.batch_alter_table("market_rates", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_market_rates_observed_at"))
        batch_op.drop_index(batch_op.f("ix_market_rates_pair"))
    op.drop_table("market_rates")

    with op.batch_alter_table("fiscal_parameters", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_fiscal_parameters_effective_to"))
        batch_op.drop_index(batch_op.f("ix_fiscal_parameters_effective_from"))
        batch_op.drop_index(batch_op.f("ix_fiscal_parameters_year"))
    op.drop_table("fiscal_parameters")
