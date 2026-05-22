"""A17.L5 — seed expandido institution_catalog (alta renda PJ + global accounts).

Revision ID: a17l5seed
Revises: adr239apolice
Create Date: 2026-05-22

Sprint A17 L5 (Onda 0 do plano LLM Prompts Hardening). Expande
``institution_catalog`` para cobrir 18 instituições alvo do público
alta renda PJ que hoje não estão no seed pós-A7.3 (apenas 8 bancos
hardcoded em prompts LLM cobertos: itau, santander, bradesco, c6bank,
btgpactual, rico, nubank, inter).

Cobertura (revisão `financial-planner`)
---------------------------------------
- 7 corretoras alta renda (XP, BTG Digital, Genial, Modal, Ágora, Toro, Warren)
- 4 contas globais USD (Avenue, Inter Invest USA, Nomad, Stake)
- 2 migrações históricas (Pi/Santander, NuInvest/ex-Easynvest)
- 3 contas-pagamento (Inter Pag, PicPay Invest, Mercado Pago)
- 2 cooperativas (Sicoob, Sicredi)

Categorias novas (string livre, sem CHECK em ``category``):
``global_account``, ``payment_account``, ``cooperative``.

Idempotente por ``code`` (UNIQUE). Migration ANSI portátil (Postgres + SQLite).
Padrão alinhado a ``adr239apolice_seed_insurance_carriers``.
"""

from datetime import datetime, timezone
from typing import Sequence, Union
from uuid import uuid4

import sqlalchemy as sa
from alembic import context, op

revision: str = "a17l5seed"
down_revision: Union[str, Sequence[str], None] = "adr239apolice"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_NEW_INSTITUTIONS: list[dict[str, str]] = [
    # Corretoras alta renda — `broker` (já em uso).
    {
        "code": "xpinvestimentos",
        "name": "XP Investimentos",
        "category": "broker",
        "tax_regime": "both",
    },
    {
        "code": "btgdigital",
        "name": "BTG Pactual Digital",
        "category": "broker",
        "tax_regime": "both",
    },
    {"code": "genial", "name": "Genial Investimentos", "category": "broker", "tax_regime": "both"},
    {"code": "modal", "name": "Modal", "category": "broker", "tax_regime": "both"},
    {"code": "agora", "name": "Ágora Investimentos", "category": "broker", "tax_regime": "both"},
    {"code": "toro", "name": "Toro Investimentos", "category": "broker", "tax_regime": "both"},
    {"code": "warren", "name": "Warren", "category": "broker", "tax_regime": "both"},
    # Contas globais USD — `global_account` (nova categoria; Wise permanece `fintech`
    # por ser conta multimoeda EU-licensed, não corretora US-only).
    {
        "code": "avenue",
        "name": "Avenue Securities",
        "category": "global_account",
        "tax_regime": "both",
    },
    {
        "code": "interinvestusa",
        "name": "Inter Invest USA",
        "category": "global_account",
        "tax_regime": "both",
    },
    {"code": "nomad", "name": "Nomad", "category": "global_account", "tax_regime": "both"},
    {"code": "stake", "name": "Stake", "category": "global_account", "tax_regime": "both"},
    # Migrações históricas (corretoras descontinuadas / renomeadas) — aparecem
    # em informes 2018-2023 mesmo após M&A; manter código distinto preserva
    # rastreabilidade para baseline patrimonial multi-ano.
    {
        "code": "pi",
        "name": "Pi Investimentos (Santander)",
        "category": "broker",
        "tax_regime": "both",
    },
    {
        "code": "nuinvest",
        "name": "NuInvest (ex-Easynvest)",
        "category": "broker",
        "tax_regime": "both",
    },
    # Contas-pagamento (fluxo de caixa, classificação fiscal distinta de banco
    # tradicional após Normativa RFB 2024) — `payment_account` (nova categoria).
    # `picpay` (banco) e `inter` (banco) permanecem; estes são produtos separados.
    {"code": "interpag", "name": "Inter Pag", "category": "payment_account", "tax_regime": "both"},
    {
        "code": "picpayinvest",
        "name": "PicPay Invest",
        "category": "payment_account",
        "tax_regime": "both",
    },
    {
        "code": "mercadopago",
        "name": "Mercado Pago",
        "category": "payment_account",
        "tax_regime": "both",
    },
    # Cooperativas de crédito — `cooperative` (nova categoria; estrutura
    # societária e tributação distintas de banco comercial).
    {"code": "sicoob", "name": "Sicoob", "category": "cooperative", "tax_regime": "both"},
    {"code": "sicredi", "name": "Sicredi", "category": "cooperative", "tax_regime": "both"},
]


def upgrade() -> None:
    """Seed 18 instituições novas (idempotent por code UNIQUE)."""
    if context.is_offline_mode():
        op.execute(
            "-- A17.L5 seed (institution_catalog expansion) skipped in offline mode; "
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
    """Remove apenas as 18 rows adicionadas por esta migration."""
    if context.is_offline_mode():
        return
    bind = op.get_bind()
    for item in _NEW_INSTITUTIONS:
        bind.execute(
            sa.text("DELETE FROM institution_catalog WHERE code = :code"),
            {"code": item["code"]},
        )
