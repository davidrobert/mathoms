"""ADR-235 A16: estende enum `classification` com `nu_proprietario`.

Revision ID: adr235nupropriet1
Revises: adr227debt1
Create Date: 2026-05-20

Adiciona valor ``nu_proprietario`` ao CHECK ``chk_classification_enum`` na
tabela ``workspace_property_overrides`` (ADR-235). Cobre imóvel em
nu-propriedade com usufruto vitalício de terceiro (cliente é dono mas
antigo proprietário detém usufruto vitalício gratuito; consolidação plena
ao falecimento do usufrutuário).

Postgres não permite editar CHECK in-place — drop + recreate via
``batch_alter_table``. Sem backfill: rows existentes preservadas.

Down: validar pre-down que nenhuma row tem ``classification='nu_proprietario'``
(raise RuntimeError se houver). Evita data loss silencioso em rollback.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import MetaData, Table

revision: str = "adr235nupropriet1"
down_revision: Union[str, Sequence[str], None] = "adr227debt1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_VALID_CLASSIFICATIONS_OLD = (
    "residencia_principal",
    "uso_pessoal",
    "locado",
    "comercial",
    "especulacao",
    "desconhecido",
)
_VALID_CLASSIFICATIONS_NEW = (
    "residencia_principal",
    "uso_pessoal",
    "locado",
    "comercial",
    "especulacao",
    "nu_proprietario",
    "desconhecido",
)


def _quote_list(values: tuple[str, ...]) -> str:
    return ",".join(f"'{v}'" for v in values)


def _overrides_table(classifications: tuple[str, ...]) -> Table:
    """Snapshot da tabela ``workspace_property_overrides`` com CHECK parametrizável.

    SQLite em offline mode (``alembic upgrade --sql``) não reflete schema;
    precisamos passar a tabela completa explicitamente em
    ``batch_alter_table(copy_from=...)``.
    """
    return Table(
        "workspace_property_overrides",
        MetaData(),
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.String(36),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "property_id",
            sa.String(36),
            sa.ForeignKey("property_identity.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("classification", sa.String(20), nullable=False),
        sa.Column(
            "override_source",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'user_manual'"),
        ),
        sa.Column(
            "created_by_user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "workspace_id",
            "property_id",
            name="uq_workspace_property",
        ),
        sa.CheckConstraint(
            f"classification IN ({_quote_list(classifications)})",
            name="chk_classification_enum",
        ),
        sa.CheckConstraint(
            "override_source IN ('user_manual','fuzzy_match_accepted','migration_keyword')",
            name="chk_override_source_enum",
        ),
    )


def upgrade() -> None:
    """Drop + recreate CHECK incluindo ``nu_proprietario``."""
    with op.batch_alter_table(
        "workspace_property_overrides",
        copy_from=_overrides_table(_VALID_CLASSIFICATIONS_OLD),
    ) as batch_op:
        batch_op.drop_constraint("chk_classification_enum", type_="check")
        batch_op.create_check_constraint(
            "chk_classification_enum",
            f"classification IN ({_quote_list(_VALID_CLASSIFICATIONS_NEW)})",
        )


def downgrade() -> None:
    """Drop + recreate CHECK sem ``nu_proprietario`` — pre-down guard."""
    # Pre-down guard: bloqueia downgrade se há rows com nu_proprietario
    # (evita data loss silencioso). Operador deve UPDATE para uso_pessoal
    # antes de rodar downgrade.
    bind = op.get_bind()
    count = bind.execute(
        sa.text(
            "SELECT COUNT(*) FROM workspace_property_overrides "
            "WHERE classification = 'nu_proprietario'"
        )
    ).scalar()
    if count and count > 0:
        raise RuntimeError(
            f"Cannot downgrade ADR-235: {count} row(s) with "
            "classification='nu_proprietario' still exist. UPDATE them to "
            "'uso_pessoal' (or another valid value) before downgrading."
        )

    with op.batch_alter_table(
        "workspace_property_overrides",
        copy_from=_overrides_table(_VALID_CLASSIFICATIONS_NEW),
    ) as batch_op:
        batch_op.drop_constraint("chk_classification_enum", type_="check")
        batch_op.create_check_constraint(
            "chk_classification_enum",
            f"classification IN ({_quote_list(_VALID_CLASSIFICATIONS_OLD)})",
        )
