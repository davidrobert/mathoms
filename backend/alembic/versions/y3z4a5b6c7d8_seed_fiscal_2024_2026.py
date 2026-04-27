"""seed fiscal_parameters 2024-2026 + market_rates current snapshot

Revision ID: y3z4a5b6c7d8
Revises: x2y3z4a5b6c7
Create Date: 2026-04-27

ADR-135 / A7.2b: data migration que materializa o conteúdo histórico de
``config/parametros_fiscais.json`` em rows de ``fiscal_parameters`` para
2024, 2025 e 2026 (mesmo conteúdo dos 3 anos — JSON corrente reflete o
estado vigente; rows futuras virão da admin UI).

E ``config/taxas.json`` em ``market_rates`` para a data corrente
(USD/BRL e EUR/BRL). Outros indexadores (CDI, SELIC, IPCA…) ficam em
config até decisão futura sobre granularidade.

Idempotente: skip silencioso se rows já existem (chave de unicidade
``year`` + ``effective_from`` para fiscal; ``UNIQUE(pair, observed_at)``
para market). Permite rodar migration em DB já populado.
"""

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "y3z4a5b6c7d8"
down_revision: Union[str, None] = "x2y3z4a5b6c7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ---------------------------------------------------------------------------
# Conteúdo histórico (mesmo de config/parametros_fiscais.json em 2026-04-08).
# Faixas IRPF anuais em cents; alíquota em pct (DECIMAL no DB).
# ---------------------------------------------------------------------------

_IR_BRACKETS_2025 = [
    {"upper_brl_cents": 2696320, "aliquota_pct": "0.0", "deducao_brl_cents": 0},
    {"upper_brl_cents": 3391980, "aliquota_pct": "7.5", "deducao_brl_cents": 0},
    {"upper_brl_cents": 4501260, "aliquota_pct": "15.0", "deducao_brl_cents": 0},
    {"upper_brl_cents": 5597616, "aliquota_pct": "22.5", "deducao_brl_cents": 0},
    {"upper_brl_cents": None, "aliquota_pct": "27.5", "deducao_brl_cents": 0},
]

_FISCAL_SOURCE = "config/parametros_fiscais.json snapshot 2026-04-27 (Receita Federal)"

# Lucro presumido = 32% (serviços) → DECIMAL 0.32; PGBL pct → trabalhamos
# com 0 cents porque o JSON legado expressa apenas como % da renda. Como
# a tabela guarda absoluto, deixamos 0 (o domain service mantém pct via
# legado até admin UI popular). Mesmo para INSS ceiling (não estava no
# JSON; default 0).
_LUCRO_PRESUMIDO = Decimal("0.32")
_PGBL_LIMIT_CENTS = 0
_INSS_CEILING_CENTS = 0


def _fiscal_row(year: int) -> dict:
    return {
        "id": str(uuid.uuid4()),
        "year": year,
        "ir_brackets": _IR_BRACKETS_2025,
        "pgbl_limit_brl_cents": _PGBL_LIMIT_CENTS,
        "inss_ceiling_brl_cents": _INSS_CEILING_CENTS,
        "lucro_presumido_aliquota": _LUCRO_PRESUMIDO,
        "effective_from": date(year, 1, 1),
        "effective_to": date(year, 12, 31),
        "source": _FISCAL_SOURCE,
        "created_at": datetime.now(timezone.utc),
    }


_MARKET_RATES_INITIAL = [
    ("USD/BRL", Decimal("5.80")),
    ("EUR/BRL", Decimal("6.35")),
]
_MARKET_SOURCE = "config/taxas.json snapshot 2026-04-27 (BCB)"

# Bootstrap histórico — sem PTAX por dia, usamos a mesma cotação corrente
# como ponto inicial em 2024-01-01 para que relatórios históricos não
# falhem com MarketRateNotFound. Backfill real entra via admin UI / API
# no futuro.
_MARKET_BOOTSTRAP_DATE = date(2024, 1, 1)
_MARKET_BOOTSTRAP_SOURCE = "bootstrap A7.2b (cotação corrente replicada para histórico)"


def upgrade() -> None:
    bind = op.get_bind()
    fiscal_table = sa.table(
        "fiscal_parameters",
        sa.column("id", sa.String),
        sa.column("year", sa.Integer),
        sa.column("ir_brackets", sa.JSON),
        sa.column("pgbl_limit_brl_cents", sa.BigInteger),
        sa.column("inss_ceiling_brl_cents", sa.BigInteger),
        sa.column("lucro_presumido_aliquota", sa.Numeric),
        sa.column("effective_from", sa.Date),
        sa.column("effective_to", sa.Date),
        sa.column("source", sa.Text),
        sa.column("created_at", sa.DateTime(timezone=True)),
    )

    existing_years = {
        r[0]
        for r in bind.execute(
            sa.text("SELECT DISTINCT year FROM fiscal_parameters")
        ).fetchall()
    }
    rows = [_fiscal_row(year) for year in (2024, 2025, 2026) if year not in existing_years]
    if rows:
        op.bulk_insert(fiscal_table, rows)

    market_table = sa.table(
        "market_rates",
        sa.column("id", sa.String),
        sa.column("pair", sa.String),
        sa.column("rate", sa.Numeric),
        sa.column("observed_at", sa.Date),
        sa.column("source", sa.Text),
        sa.column("created_at", sa.DateTime(timezone=True)),
    )
    today = date(2026, 4, 27)
    existing_pairs = {
        (r[0], str(r[1]))
        for r in bind.execute(
            sa.text("SELECT pair, observed_at FROM market_rates")
        ).fetchall()
    }
    market_rows: list[dict] = []
    for (pair, rate) in _MARKET_RATES_INITIAL:
        for observed, source in (
            (_MARKET_BOOTSTRAP_DATE, _MARKET_BOOTSTRAP_SOURCE),
            (today, _MARKET_SOURCE),
        ):
            if (pair, observed.isoformat()) in existing_pairs:
                continue
            market_rows.append(
                {
                    "id": str(uuid.uuid4()),
                    "pair": pair,
                    "rate": rate,
                    "observed_at": observed,
                    "source": source,
                    "created_at": datetime.now(timezone.utc),
                }
            )
    if market_rows:
        op.bulk_insert(market_table, market_rows)


def downgrade() -> None:
    """Remove apenas as rows seedadas — não dropa tabelas."""
    bind = op.get_bind()
    bind.execute(
        sa.text("DELETE FROM fiscal_parameters WHERE source = :src"),
        {"src": _FISCAL_SOURCE},
    )
    bind.execute(
        sa.text("DELETE FROM market_rates WHERE source IN (:src1, :src2)"),
        {"src1": _MARKET_SOURCE, "src2": _MARKET_BOOTSTRAP_SOURCE},
    )
