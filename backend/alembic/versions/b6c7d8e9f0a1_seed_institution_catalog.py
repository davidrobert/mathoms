"""seed institution_catalog from config/institutions.json (A7.3 · ADR-137)

Revision ID: b6c7d8e9f0a1
Revises: a5b6c7d8e9f0
Create Date: 2026-04-27

Popula ``institution_catalog`` com o canonical de bancos/corretoras/exchanges
suportados em ``config/institutions.json``. Categoria classificada
heuristicamente do nome (banco/corretora/exchange/seguradora/agência/outro).

Idempotente: skip silencioso se row com mesmo ``code`` já existe (UNIQUE).
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Sequence, Union

import sqlalchemy as sa
from alembic import context, op

revision: str = "b6c7d8e9f0a1"
down_revision: Union[str, None] = "a5b6c7d8e9f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_INSTITUTIONS: list[dict[str, Any]] = [
    {"code": "bankofamerica", "name": "Bank of America", "category": "bank"},
    {"code": "btgpactual", "name": "BTG Pactual", "category": "broker"},
    {"code": "c6bank", "name": "C6 Bank", "category": "bank"},
    {"code": "picpay", "name": "PicPay", "category": "bank"},
    {"code": "bradesco", "name": "Bradesco", "category": "bank"},
    {"code": "itau", "name": "Itaú", "category": "bank"},
    {"code": "santander", "name": "Santander", "category": "bank"},
    {"code": "rico", "name": "Rico", "category": "broker"},
    {"code": "wise", "name": "Wise", "category": "fintech"},
    {"code": "binance", "name": "Binance", "category": "exchange"},
    {"code": "receitafederal", "name": "Receita Federal", "category": "government"},
    {"code": "quintoandar", "name": "QuintoAndar", "category": "real_estate"},
    {"code": "einstein", "name": "Einstein", "category": "employer"},
    {"code": "caixa", "name": "Caixa Econômica Federal", "category": "bank"},
    {"code": "stone", "name": "Stone", "category": "fintech"},
    {"code": "nubank", "name": "Nubank", "category": "bank"},
    {"code": "inter", "name": "Inter", "category": "bank"},
]


def upgrade() -> None:
    if context.is_offline_mode():
        op.execute(
            "-- A7.3 seed (institution_catalog) skipped in offline mode; "
            "run via online migration on target DB."
        )
        return

    catalog_table = sa.table(
        "institution_catalog",
        sa.column("id", sa.String),
        sa.column("code", sa.String),
        sa.column("name", sa.String),
        sa.column("default_parser", sa.String),
        sa.column("category", sa.String),
        sa.column("metadata_json", sa.JSON),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )

    existing = _query_existing_codes()
    now = datetime.now(timezone.utc)
    rows = [
        {
            "id": str(uuid.uuid4()),
            "code": item["code"],
            "name": item["name"],
            "default_parser": None,
            "category": item["category"],
            "metadata_json": {},
            "created_at": now,
            "updated_at": now,
        }
        for item in _INSTITUTIONS
        if item["code"] not in existing
    ]
    if rows:
        op.bulk_insert(catalog_table, rows)


def _query_existing_codes() -> set[str]:
    try:
        bind = op.get_bind()
        return {
            r[0] for r in bind.execute(sa.text("SELECT code FROM institution_catalog")).fetchall()
        }
    except (AttributeError, Exception):
        return set()


def downgrade() -> None:
    bind = op.get_bind()
    codes = [item["code"] for item in _INSTITUTIONS]
    bind.execute(
        sa.text("DELETE FROM institution_catalog WHERE code IN (:codes)"),
        {"codes": ",".join(codes)},
    )
