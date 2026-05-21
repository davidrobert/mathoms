"""ADR-238: institution_catalog tax_regime + insurance category + brasilprev seed (A17 L1 P1).

Revision ID: adr238informes1
Revises: adr236bizprofile1
Create Date: 2026-05-21

ADR-238 D7 (catálogo institucional): expande ``institution_catalog`` para
suportar instituições emissoras de informes de rendimentos anuais avulsos
(BrasilPrev na L1; XP / Itaúsa nas lanes L3/L4).

Mudanças
--------
1. **Nova coluna ``tax_regime``** ``Literal["pf", "pj", "both"]`` default ``"both"``.
   Server-default + Python-default + not-null — toda instituição já existente
   herda ``both`` (compatível com C6, Stone, Wise que servem PF + PJ).
2. **Categoria ``insurance``** disponível (sem migration de tipo — ``category``
   é ``String(20)`` livre desde A7.3). Documenta o valor para futuras lanes.
   ``broker`` e ``holding`` também passam a ser valores reconhecidos
   (``broker`` já em uso por BTG/Rico/XP).
3. **Seed ``brasilprev``** (``insurance``, ``both``) — idempotente por
   ``code`` (UNIQUE). XP e Itaúsa entram nas lanes A17 L3/L4.

Compatibilidade
---------------
``ADR-097`` extract-then-refactor: coluna nova com default; consumers
existentes não enxergam mudança. ``InstitutionCatalog`` model será
atualizado em PR seguinte (não trivial — exige refatorar testes que
instanciam a classe diretamente).
"""

from datetime import datetime, timezone
from typing import Sequence, Union
from uuid import uuid4

import sqlalchemy as sa
from alembic import context, op

revision: str = "adr238informes1"
down_revision: Union[str, Sequence[str], None] = "adr236bizprofile1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_NEW_INSTITUTIONS: list[dict[str, str]] = [
    # ADR-238 L1 — BrasilPrev (seguradora de previdência privada).
    # Cobre famílias BrasilPrev (Banco do Brasil), por extensão Bradesco
    # Vida, Caixa Vida e Icatu quando esses informes entrarem.
    {"code": "brasilprev", "name": "BrasilPrev", "category": "insurance", "tax_regime": "both"},
]


def upgrade() -> None:
    """Add ``tax_regime`` column + CHECK + seed BrasilPrev (idempotent)."""
    with op.batch_alter_table("institution_catalog") as batch:
        batch.add_column(
            sa.Column(
                "tax_regime",
                sa.String(8),
                nullable=False,
                server_default="both",
            )
        )
        batch.create_check_constraint(
            "ck_institution_catalog_tax_regime",
            "tax_regime IN ('pf', 'pj', 'both')",
        )

    if context.is_offline_mode():
        op.execute(
            "-- ADR-238 seed (brasilprev) skipped in offline mode; "
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
    """Remove ``tax_regime`` column + CHECK + seeded rows."""
    if not context.is_offline_mode():
        bind = op.get_bind()
        for item in _NEW_INSTITUTIONS:
            bind.execute(
                sa.text("DELETE FROM institution_catalog WHERE code = :code"),
                {"code": item["code"]},
            )

    # Tolerar ausência de CHECK em rollback de versão pré-CHECK desta mesma
    # revisão (sem-op se constraint não existe — comum em DBs criados antes
    # do ajuste pós-gate data-engineer 2026-05-21).
    try:
        with op.batch_alter_table("institution_catalog") as batch:
            batch.drop_constraint("ck_institution_catalog_tax_regime", type_="check")
    except (ValueError, Exception):
        pass

    with op.batch_alter_table("institution_catalog") as batch:
        batch.drop_column("tax_regime")
