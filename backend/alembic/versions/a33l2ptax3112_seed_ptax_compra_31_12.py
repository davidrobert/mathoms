"""seed market_rates — PTAX compra 31/12 real (2023-2025, USD/EUR/GBP)

Revision ID: a33l2ptax3112
Revises: a31l1opsaudit
Create Date: 2026-07-07

A33.l2 (ADR-238 D5 · emenda ADR-135): o seed A7.2b (``y3z4a5b6c7d8``)
bootstrapa 2024-01-01 replicando a cotação de 2026-04-27 — lookup
``get_latest_on_or_before(pair, 31/12/ano)`` caía na row de bootstrap com
valor errado, silenciosamente. Este seed materializa a PTAX de **compra**
(boletim de fechamento, API Olinda BCB) em ``observed_at = 31/12`` de cada
ano-base relevante para informes (onboarding aceita 2 anos retro + ano
corrente):

- 31/12/2023 (fechamento do último dia útil, 2023-12-29):
  USD 4,8407 · EUR 5,3490 · GBP 6,1559
- 31/12/2024: USD 6,1917 · EUR 6,4344 · GBP 7,7570
- 31/12/2025: USD 5,5018 · EUR 6,4679 · GBP 7,4098

Convenção: ``rate`` para ``*/BRL`` é PTAX de compra (mesma base RFB para
bens/direitos e GCAP) — emenda ADR-135. Idempotente: skip silencioso se
``(pair, observed_at)`` já existe. Downgrade deleta por ``source``.
"""

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import context, op

revision: str = "a33l2ptax3112"
down_revision: Union[str, None] = "a31l1opsaudit"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _source(ano: int, quote_date: str) -> str:
    return f"BCB PTAX compra 31/12/{ano} (boletim fechamento {quote_date}, API Olinda)"


#: (pair, rate compra, observed_at, source). Valores oficiais BCB Olinda
#: (CotacaoDolarDia / CotacaoMoedaDia, boletim "Fechamento PTAX").
_PTAX_ROWS: list[tuple[str, Decimal, date, str]] = [
    ("USD/BRL", Decimal("4.8407"), date(2023, 12, 31), _source(2023, "2023-12-29")),
    ("EUR/BRL", Decimal("5.3490"), date(2023, 12, 31), _source(2023, "2023-12-29")),
    ("GBP/BRL", Decimal("6.1559"), date(2023, 12, 31), _source(2023, "2023-12-29")),
    ("USD/BRL", Decimal("6.1917"), date(2024, 12, 31), _source(2024, "2024-12-31")),
    ("EUR/BRL", Decimal("6.4344"), date(2024, 12, 31), _source(2024, "2024-12-31")),
    ("GBP/BRL", Decimal("7.7570"), date(2024, 12, 31), _source(2024, "2024-12-31")),
    ("USD/BRL", Decimal("5.5018"), date(2025, 12, 31), _source(2025, "2025-12-31")),
    ("EUR/BRL", Decimal("6.4679"), date(2025, 12, 31), _source(2025, "2025-12-31")),
    ("GBP/BRL", Decimal("7.4098"), date(2025, 12, 31), _source(2025, "2025-12-31")),
]

_ALL_SOURCES = sorted({row[3] for row in _PTAX_ROWS})


def upgrade() -> None:
    if context.is_offline_mode():
        op.execute(
            "-- A33.l2 seed (market_rates PTAX compra 31/12) skipped in offline mode; "
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
    rows = [
        {
            "id": str(uuid.uuid4()),
            "pair": pair,
            "rate": rate,
            "observed_at": observed,
            "source": source,
            "created_at": datetime.now(timezone.utc),
        }
        for pair, rate, observed, source in _PTAX_ROWS
        if (pair, observed.isoformat()) not in existing
    ]
    if rows:
        op.bulk_insert(market_table, rows)


def _query_existing_pairs() -> set[tuple[str, str]]:
    """Idempotência online; em offline mode, sempre retorna empty."""
    try:
        bind = op.get_bind()
        return {
            (r[0], str(r[1]))
            for r in bind.execute(sa.text("SELECT pair, observed_at FROM market_rates")).fetchall()
        }
    except (AttributeError, Exception):  # offline mode (--sql) → no live connection
        return set()


def downgrade() -> None:
    """Remove apenas as rows seedadas — não dropa tabela."""
    bind = op.get_bind()
    for src in _ALL_SOURCES:
        bind.execute(sa.text("DELETE FROM market_rates WHERE source = :src"), {"src": src})
