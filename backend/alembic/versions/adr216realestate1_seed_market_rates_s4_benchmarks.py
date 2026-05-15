"""ADR-216 P-A: seed market_rates com benchmarks do card S4 (CDI, NTNB_REAL_10Y, IFIX_YIELD_12M).

Revision ID: adr216realestate1
Revises: adr215residencia1
Create Date: 2026-05-15

Adiciona 3 pairs novos ao `market_rates` (ADR-135 schema já existente).
Convenção fixada em [FORMULAS.md §Imóveis] + ADR-216 D2:

- `CDI`              — taxa nominal anual (% a.a., pré-IR; normalização vira no adapter)
- `NTNB_REAL_10Y`    — yield real anual interpolado para vértice 10 anos (% a.a. real, pré-IR)
- `IFIX_YIELD_12M`   — dividend yield trailing 12m do IFIX (% a.a., isento IR PF)

Seed inicial = 1 valor por pair, snapshot 2026-05-15. Série temporal (Bacen
SGS / Tesouro Direto / B3 ANBIMA) entra em lane separada quando produto for
multi-workspace; v1 dogfood usa o snapshot.

Idempotente: skip silencioso se `UNIQUE(pair, observed_at)` já existe.
"""

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import context, op

revision: str = "adr216realestate1"
down_revision: Union[str, Sequence[str], None] = "adr215residencia1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_SEED_DATE = date(2026, 5, 15)
_SEED_SOURCE = (
    "ADR-216 P-A snapshot 2026-05-15 (Bacen SGS 12 CDI · Tesouro Direto NTN-B 10y · B3 IFIX 12m)"
)

# Valores observados em 2026-05-15. Documentação dos números:
# - CDI: Selic 10,9% (mai/2026); pre-fixed CDI ≈ Selic
# - NTNB_REAL_10Y: yield real ~6,5% a.a. interpolado entre NTN-B 2035 e 2045
# - IFIX_YIELD_12M: dividend yield trailing 12m do índice IFIX ~9,2%
_BENCHMARKS_INITIAL = [
    ("CDI", Decimal("10.90")),
    ("NTNB_REAL_10Y", Decimal("6.50")),
    ("IFIX_YIELD_12M", Decimal("9.20")),
]


def upgrade() -> None:
    if context.is_offline_mode():
        op.execute(
            "-- ADR-216 P-A seed (market_rates S4 benchmarks) skipped in offline mode; "
            "run via online migration on target DB."
        )
        return

    market_table = sa.table(
        "market_rates",
        sa.column("id", sa.String),
        sa.column("pair", sa.String),
        sa.column("rate", sa.Numeric),
        sa.column("observed_at", sa.Date),
        sa.column("source", sa.Text),
        sa.column("created_at", sa.DateTime(timezone=True)),
    )

    existing = _query_existing_pairs()
    rows: list[dict] = []
    for pair, rate in _BENCHMARKS_INITIAL:
        if (pair, _SEED_DATE.isoformat()) in existing:
            continue
        rows.append(
            {
                "id": str(uuid.uuid4()),
                "pair": pair,
                "rate": rate,
                "observed_at": _SEED_DATE,
                "source": _SEED_SOURCE,
                "created_at": datetime.now(timezone.utc),
            }
        )
    if rows:
        op.bulk_insert(market_table, rows)


def _query_existing_pairs() -> set[tuple[str, str]]:
    """Idempotência online; em offline mode, sempre retorna empty."""
    if context.is_offline_mode():
        return set()
    bind = op.get_bind()
    result = bind.execute(
        sa.text(
            "SELECT pair, observed_at FROM market_rates "
            "WHERE pair IN ('CDI', 'NTNB_REAL_10Y', 'IFIX_YIELD_12M')"
        )
    )
    return {
        (row[0], row[1].isoformat() if hasattr(row[1], "isoformat") else row[1]) for row in result
    }


def downgrade() -> None:
    if context.is_offline_mode():
        op.execute("-- ADR-216 P-A seed downgrade skipped in offline mode.")
        return
    bind = op.get_bind()
    bind.execute(
        sa.text(
            "DELETE FROM market_rates "
            "WHERE pair IN ('CDI', 'NTNB_REAL_10Y', 'IFIX_YIELD_12M') "
            "AND source LIKE 'ADR-216 P-A%'"
        )
    )
