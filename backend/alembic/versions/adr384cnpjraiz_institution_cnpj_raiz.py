"""ADR-384: institution_catalog.cnpj_raiz — identidade institucional por CNPJ-raiz (A40.l40).

Revision ID: adr384cnpjraiz
Revises: adr378expira
Create Date: 2026-08-12

Coluna ``cnpj_raiz`` String(8) NULL + index NÃO-único + CHECK de formato
(8 dígitos). Raiz de 8 dígitos, não CNPJ completo: banco tem N
estabelecimentos e match exato de 14 dígitos falha estreito e silencioso
na maioria dos informes (ADR-384 §2, veto data-engineer). Colisão de raiz
(holding × banco) resolve por ``category`` no matcher, não por constraint.
Seed dos valores em migration de dados separada (``adr384cnpjseed``).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import MetaData, Table

revision: str = "adr384cnpjraiz"
down_revision: Union[str, Sequence[str], None] = "adr378expira"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _institution_catalog_pre() -> Table:
    """Snapshot pré-ADR-384 (sem ``cnpj_raiz``) — habilita batch_alter_table em SQLite --sql offline."""
    return Table(
        "institution_catalog",
        MetaData(),
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("code", sa.String(50), nullable=False, unique=True, index=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("default_parser", sa.String(80), nullable=True),
        sa.Column("category", sa.String(20), nullable=False),
        sa.Column("tax_regime", sa.String(8), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "tax_regime IN ('pf', 'pj', 'both')",
            name="ck_institution_catalog_tax_regime",
        ),
    )


def _institution_catalog_post() -> Table:
    """Snapshot pós-ADR-384 (com ``cnpj_raiz``) — habilita batch_alter_table no downgrade."""
    pre = _institution_catalog_pre()
    pre.append_column(sa.Column("cnpj_raiz", sa.String(8), nullable=True))
    pre.append_constraint(
        sa.CheckConstraint(
            "cnpj_raiz IS NULL OR (length(cnpj_raiz) = 8 AND cnpj_raiz GLOB '[0-9]*' "
            "AND cnpj_raiz NOT GLOB '*[^0-9]*')",
            name="ck_institution_catalog_cnpj_raiz",
        )
    )
    return pre


def upgrade() -> None:
    with op.batch_alter_table("institution_catalog", copy_from=_institution_catalog_pre()) as batch:
        batch.add_column(sa.Column("cnpj_raiz", sa.String(8), nullable=True))
        batch.create_check_constraint(
            "ck_institution_catalog_cnpj_raiz",
            "cnpj_raiz IS NULL OR (length(cnpj_raiz) = 8 AND cnpj_raiz GLOB '[0-9]*' "
            "AND cnpj_raiz NOT GLOB '*[^0-9]*')",
        )
    op.create_index(
        "ix_institution_catalog_cnpj_raiz",
        "institution_catalog",
        ["cnpj_raiz"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_institution_catalog_cnpj_raiz", table_name="institution_catalog")
    with op.batch_alter_table(
        "institution_catalog", copy_from=_institution_catalog_post()
    ) as batch:
        batch.drop_constraint("ck_institution_catalog_cnpj_raiz", type_="check")
        batch.drop_column("cnpj_raiz")
