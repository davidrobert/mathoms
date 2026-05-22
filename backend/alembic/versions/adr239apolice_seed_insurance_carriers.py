"""ADR-239 L2: seed seguradoras top no institution_catalog (A18 L2 P2).

Revision ID: adr239apolice
Revises: adr241index
Create Date: 2026-05-22

ADR-239 D9 (catálogo institucional): adiciona top-5 seguradoras brasileiras
que aparecem em apólices V1 (auto, residencial, combinada). Categoria
``insurance`` já existe desde ADR-238 (BrasilPrev seed); aqui só adicionamos
novas rows.

Seed idempotente por ``code`` (UNIQUE). Migration ANSI portátil (Postgres + SQLite).
"""

from datetime import datetime, timezone
from typing import Sequence, Union
from uuid import uuid4

import sqlalchemy as sa
from alembic import context, op

revision: str = "adr239apolice"
down_revision: Union[str, Sequence[str], None] = "adr241index"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ADR-239 L2 — top-5 seguradoras brasileiras (categoria=insurance). Lista
# alinhada ao briefing data-engineer + corretoras observadas no batch dogfood
# 2026-05-21 (Porto, Tokio Marine, Bradesco). Itaú/Zurich complementam mercado.
_NEW_INSURANCE_CARRIERS: list[dict[str, str]] = [
    {"code": "porto", "name": "Porto Seguro", "category": "insurance", "tax_regime": "both"},
    {
        "code": "tokiomarine",
        "name": "Tokio Marine Seguradora",
        "category": "insurance",
        "tax_regime": "both",
    },
    {
        "code": "bradesco_seguros",
        "name": "Bradesco Seguros",
        "category": "insurance",
        "tax_regime": "both",
    },
    {"code": "itau_seguros", "name": "Itaú Seguros", "category": "insurance", "tax_regime": "both"},
    {
        "code": "zurich",
        "name": "Zurich Minas Brasil",
        "category": "insurance",
        "tax_regime": "both",
    },
]


def upgrade() -> None:
    """Seed seguradoras top-5 (idempotent por code UNIQUE)."""
    if context.is_offline_mode():
        op.execute(
            "-- ADR-239 L2 seed (insurance carriers) skipped in offline mode; "
            "run via online migration on target DB."
        )
        return

    bind = op.get_bind()
    existing = {
        r[0] for r in bind.execute(sa.text("SELECT code FROM institution_catalog")).fetchall()
    }
    now = datetime.now(timezone.utc)
    rows = [
        {
            "id": str(uuid4()),
            "code": item["code"],
            "name": item["name"],
            "default_parser": None,
            "category": item["category"],
            "tax_regime": item["tax_regime"],
            "metadata_json": {},
            "created_at": now,
            "updated_at": now,
        }
        for item in _NEW_INSURANCE_CARRIERS
        if item["code"] not in existing
    ]
    if rows:
        catalog_table = sa.table(
            "institution_catalog",
            sa.column("id", sa.String),
            sa.column("code", sa.String),
            sa.column("name", sa.String),
            sa.column("default_parser", sa.String),
            sa.column("category", sa.String),
            sa.column("tax_regime", sa.String),
            sa.column("metadata_json", sa.JSON),
            sa.column("created_at", sa.DateTime(timezone=True)),
            sa.column("updated_at", sa.DateTime(timezone=True)),
        )
        op.bulk_insert(catalog_table, rows)


def downgrade() -> None:
    """Remove seeded carriers (mantém categoria 'insurance' que já tem BrasilPrev)."""
    if context.is_offline_mode():
        return
    bind = op.get_bind()
    for item in _NEW_INSURANCE_CARRIERS:
        bind.execute(
            sa.text("DELETE FROM institution_catalog WHERE code = :code"),
            {"code": item["code"]},
        )
