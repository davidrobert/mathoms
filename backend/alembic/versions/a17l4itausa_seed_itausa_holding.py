"""A17.L4 — seed Itaúsa em institution_catalog como category=holding.

Revision ID: a17l4itausa
Revises: a20l12semver
Create Date: 2026-07-02

Critério de aceite de A17.L4 (proventos ações): "Itaúsa entra em
`institutions` como `category=holding`". Informe anual da Itaúsa
(`tipo_informe=proventos_acoes`, 1 ativo ITSA4) referencia a holding
como emissor — sem a row, `institution_catalog` não resolve o código
canônico e o artifact fica sem instituição atribuída.

Categoria ``holding`` já é valor reconhecido desde
``adr238informes1_institutions_tax_regime_categories`` (string livre,
sem CHECK). Idempotente por ``code`` (UNIQUE); ANSI portátil
(Postgres + SQLite). Padrão de ``a17l5seed_expand_institution_catalog``.
"""

from datetime import datetime, timezone
from typing import Sequence, Union
from uuid import uuid4

import sqlalchemy as sa
from alembic import context, op

revision: str = "a17l4itausa"
down_revision: Union[str, Sequence[str], None] = "a20l12semver"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_NEW_INSTITUTIONS: list[dict[str, str]] = [
    {"code": "itausa", "name": "Itaúsa S.A.", "category": "holding", "tax_regime": "both"},
]


def upgrade() -> None:
    """Seed Itaúsa (idempotente por code UNIQUE)."""
    if context.is_offline_mode():
        op.execute(
            "-- A17.L4 seed (itausa holding) skipped in offline mode; "
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
        for item in _NEW_INSTITUTIONS
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
    """Remove apenas a row adicionada por esta migration."""
    if context.is_offline_mode():
        return
    bind = op.get_bind()
    for item in _NEW_INSTITUTIONS:
        bind.execute(
            sa.text("DELETE FROM institution_catalog WHERE code = :code"),
            {"code": item["code"]},
        )
