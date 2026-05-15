"""ADR-215 A12 P1: workspaces.residencia_status + property_identity + workspace_property_overrides.

Revision ID: adr215residencia1
Revises: adr212drop9
Create Date: 2026-05-15

Schema base do override de classificação de imóveis (ADR-215). 3 mudanças:

1. ``workspaces.residencia_status`` VARCHAR(20) NOT NULL DEFAULT 'undeclared'
   com CHECK ``status IN ('owned','rented','undeclared')``. Tripartite:
   ``owned`` = família tem residência (1 override deve existir);
   ``rented`` = mora alugado (linha "Residência" no relatório esconde);
   ``undeclared`` = ainda não respondeu (default).

2. Tabela ``property_identity`` — identidade estável de imóvel cross-IRPFs
   gerada pelo consolidador E1.5c. Match por
   ``(workspace_id, titular_key, codigo_rfb, endereco_canonical)``;
   ``low_confidence`` marca casos de ambiguidade que UI resolve manualmente.

3. Tabela ``workspace_property_overrides`` — override DB-first do
   ``classification`` enum por imóvel. Partial unique index garante 1
   ``residencia_principal`` por workspace.

P1 não muda comportamento do pipeline (P2/P3 consomem). Migration é
aditiva — colunas e tabelas existem mas não são lidas até P2/P3.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import MetaData, Table

revision: str = "adr215residencia1"
down_revision: Union[str, Sequence[str], None] = "adr214checkcode"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _workspaces_pre() -> Table:
    """Snapshot pré-upgrade do schema ``workspaces`` (post ADR-212 PR4).

    SQLite em offline mode (``alembic upgrade --sql``) não reflete schema;
    precisamos passar a tabela completa explicitamente em
    ``batch_alter_table(copy_from=...)``.
    """
    return Table(
        "workspaces",
        MetaData(),
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("family_surname", sa.String(255), nullable=True),
        sa.Column(
            "owner_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "monthly_llm_budget_usd",
            sa.Numeric(10, 2),
            nullable=False,
            server_default="5.00",
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("business_profile_json", sa.JSON(), nullable=True),
        sa.Column("rule_cap_override", sa.Integer(), nullable=True),
    )


def _workspaces_post() -> Table:
    """Snapshot pós-upgrade — com ``residencia_status``."""
    return Table(
        "workspaces",
        MetaData(),
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("family_surname", sa.String(255), nullable=True),
        sa.Column(
            "owner_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "monthly_llm_budget_usd",
            sa.Numeric(10, 2),
            nullable=False,
            server_default="5.00",
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("business_profile_json", sa.JSON(), nullable=True),
        sa.Column("rule_cap_override", sa.Integer(), nullable=True),
        sa.Column(
            "residencia_status",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'undeclared'"),
        ),
    )


_VALID_CLASSIFICATIONS = (
    "residencia_principal",
    "uso_pessoal",
    "locado",
    "comercial",
    "especulacao",
    "desconhecido",
)
_VALID_OVERRIDE_SOURCES = (
    "user_manual",
    "fuzzy_match_accepted",
    "migration_keyword",
)
_VALID_RESIDENCIA_STATUS = ("owned", "rented", "undeclared")


def _quote_list(values: tuple[str, ...]) -> str:
    return ",".join(f"'{v}'" for v in values)


def upgrade() -> None:
    """Add residencia_status to workspaces; create property_identity + workspace_property_overrides."""
    # 1) workspaces.residencia_status — server default 'undeclared' cobre backfill.
    with op.batch_alter_table("workspaces", copy_from=_workspaces_pre()) as batch_op:
        batch_op.add_column(
            sa.Column(
                "residencia_status",
                sa.String(length=20),
                nullable=False,
                server_default=sa.text("'undeclared'"),
            )
        )

    # 2) property_identity — UUID estável + chave composta de matching.
    op.create_table(
        "property_identity",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.String(length=36),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("titular_key", sa.String(length=64), nullable=False),
        sa.Column("codigo_rfb", sa.String(length=4), nullable=False),
        sa.Column("endereco_canonical", sa.String(length=255), nullable=True),
        sa.Column("first_seen_year", sa.Integer(), nullable=False),
        sa.Column("descricao_sample", sa.Text(), nullable=True),
        sa.Column(
            "low_confidence",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_property_identity_workspace_id",
        "property_identity",
        ["workspace_id"],
    )
    op.create_index(
        "ix_property_identity_lookup",
        "property_identity",
        ["workspace_id", "titular_key", "codigo_rfb", "endereco_canonical"],
    )

    # 3) workspace_property_overrides — classificação user-driven por imóvel.
    op.create_table(
        "workspace_property_overrides",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.String(length=36),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "property_id",
            sa.String(length=36),
            sa.ForeignKey("property_identity.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "classification",
            sa.String(length=20),
            nullable=False,
        ),
        sa.Column(
            "override_source",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'user_manual'"),
        ),
        sa.Column(
            "created_by_user_id",
            sa.String(length=36),
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
            f"classification IN ({_quote_list(_VALID_CLASSIFICATIONS)})",
            name="chk_classification_enum",
        ),
        sa.CheckConstraint(
            f"override_source IN ({_quote_list(_VALID_OVERRIDE_SOURCES)})",
            name="chk_override_source_enum",
        ),
    )
    op.create_index(
        "ix_workspace_property_overrides_workspace_id",
        "workspace_property_overrides",
        ["workspace_id"],
    )
    # Partial unique: 1 residencia_principal por workspace.
    op.create_index(
        "uq_workspace_one_residencia_principal",
        "workspace_property_overrides",
        ["workspace_id"],
        unique=True,
        sqlite_where=sa.text("classification = 'residencia_principal'"),
        postgresql_where=sa.text("classification = 'residencia_principal'"),
    )


def downgrade() -> None:
    """Drop overrides + identity + residencia_status."""
    op.drop_index(
        "uq_workspace_one_residencia_principal",
        table_name="workspace_property_overrides",
    )
    op.drop_index(
        "ix_workspace_property_overrides_workspace_id",
        table_name="workspace_property_overrides",
    )
    op.drop_table("workspace_property_overrides")

    op.drop_index(
        "ix_property_identity_lookup",
        table_name="property_identity",
    )
    op.drop_index(
        "ix_property_identity_workspace_id",
        table_name="property_identity",
    )
    op.drop_table("property_identity")

    with op.batch_alter_table("workspaces", copy_from=_workspaces_post()) as batch_op:
        batch_op.drop_column("residencia_status")
