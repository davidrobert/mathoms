"""ADR-219 wave 1: economic_asset_class + economic_assumptions + workspace override (3 tables + lookup seed)."""

from datetime import datetime, timezone
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import context, op

revision: str = "adr219wave1"
down_revision: Union[str, None] = "adr216realestate1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# 10 classes AUVP canônicas seedadas com a migration. Operador adiciona
# (cripto, commodities, private equity, debêntures incentivadas) via console
# interno futuro sem migration.
_INITIAL_ASSET_CLASSES: list[dict] = [
    {"code": "caixa", "label": "Caixa / Liquidez", "sort_order": 5},
    {"code": "rf_pos", "label": "Renda Fixa pós-fixada (CDI, Selic)", "sort_order": 10},
    {"code": "rf_pre", "label": "Renda Fixa prefixada", "sort_order": 20},
    {"code": "rf_inflacao", "label": "Renda Fixa indexada à inflação (IPCA+)", "sort_order": 30},
    {"code": "acoes_br", "label": "Ações Brasil", "sort_order": 40},
    {"code": "acoes_intl", "label": "Ações Internacional", "sort_order": 50},
    {"code": "fii", "label": "Fundos Imobiliários (FII)", "sort_order": 60},
    {"code": "imoveis_diretos", "label": "Imóveis físicos", "sort_order": 70},
    {"code": "cambio_usd", "label": "Câmbio USD", "sort_order": 80},
    {"code": "cambio_eur", "label": "Câmbio EUR", "sort_order": 81},
]


def _create_asset_class_table() -> None:
    op.create_table(
        "economic_asset_class",
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("label", sa.String(length=120), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("deprecated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("code"),
    )
    with op.batch_alter_table("economic_asset_class", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_economic_asset_class_active"), ["active"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_economic_asset_class_sort_order"), ["sort_order"], unique=False
        )


def _assumptions_columns() -> list:
    return [
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("classe_auvp", sa.String(length=40), nullable=False),
        sa.Column(
            "retorno_real_esperado_pct_anual", sa.Numeric(precision=6, scale=3), nullable=False
        ),
        sa.Column("sigma_anual_pct", sa.Numeric(precision=6, scale=3), nullable=False),
        sa.Column("fonte", sa.Text(), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("created_by", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    ]


def _create_assumptions_table() -> None:
    op.create_table(
        "economic_assumptions",
        *_assumptions_columns(),
        sa.ForeignKeyConstraint(
            ["classe_auvp"], ["economic_asset_class.code"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "classe_auvp", "effective_from", name="uq_economic_assumptions_classe_from"
        ),
    )
    _idx_assumptions()


def _idx_assumptions() -> None:
    with op.batch_alter_table("economic_assumptions", schema=None) as batch_op:
        for col in ("classe_auvp", "effective_from", "effective_to"):
            batch_op.create_index(batch_op.f(f"ix_economic_assumptions_{col}"), [col], unique=False)


def _override_columns() -> list:
    return [
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("classe_auvp", sa.String(length=40), nullable=False),
        sa.Column(
            "retorno_real_esperado_pct_anual", sa.Numeric(precision=6, scale=3), nullable=False
        ),
        sa.Column("sigma_anual_pct", sa.Numeric(precision=6, scale=3), nullable=False),
        sa.Column("fonte", sa.Text(), nullable=False),
        sa.Column("justificativa", sa.Text(), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("created_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    ]


def _create_override_table() -> None:
    op.create_table(
        "workspace_economic_assumptions_override",
        *_override_columns(),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["classe_auvp"], ["economic_asset_class.code"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "workspace_id",
            "classe_auvp",
            "effective_from",
            name="uq_ws_econ_override_ws_classe_from",
        ),
    )
    _idx_override()


def _idx_override() -> None:
    with op.batch_alter_table("workspace_economic_assumptions_override", schema=None) as batch_op:
        for col in ("workspace_id", "classe_auvp", "effective_from"):
            batch_op.create_index(batch_op.f(f"ix_ws_econ_override_{col}"), [col], unique=False)


def _lookup_table_proxy():
    return sa.table(
        "economic_asset_class",
        sa.column("code", sa.String),
        sa.column("label", sa.String),
        sa.column("sort_order", sa.Integer),
        sa.column("active", sa.Boolean),
        sa.column("deprecated_at", sa.DateTime(timezone=True)),
        sa.column("description", sa.Text),
        sa.column("created_at", sa.DateTime(timezone=True)),
    )


def _seed_lookup_idempotent() -> None:
    if context.is_offline_mode():
        op.execute("-- ADR-219 seed skipped in offline mode; rerun online migration.")
        return
    existing = _query_existing_codes()
    now = datetime.now(timezone.utc)
    rows = [
        {**row, "active": True, "deprecated_at": None, "description": None, "created_at": now}
        for row in _INITIAL_ASSET_CLASSES
        if row["code"] not in existing
    ]
    if rows:
        op.bulk_insert(_lookup_table_proxy(), rows)


def upgrade() -> None:
    _create_asset_class_table()
    _create_assumptions_table()
    _create_override_table()
    _seed_lookup_idempotent()


def _query_existing_codes() -> set[str]:
    try:
        bind = op.get_bind()
        return {
            r[0] for r in bind.execute(sa.text("SELECT code FROM economic_asset_class")).fetchall()
        }
    except (AttributeError, Exception):
        return set()


def downgrade() -> None:
    with op.batch_alter_table("workspace_economic_assumptions_override", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_ws_econ_override_effective_from"))
        batch_op.drop_index(batch_op.f("ix_ws_econ_override_classe_auvp"))
        batch_op.drop_index(batch_op.f("ix_ws_econ_override_workspace_id"))
    op.drop_table("workspace_economic_assumptions_override")

    with op.batch_alter_table("economic_assumptions", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_economic_assumptions_effective_to"))
        batch_op.drop_index(batch_op.f("ix_economic_assumptions_effective_from"))
        batch_op.drop_index(batch_op.f("ix_economic_assumptions_classe_auvp"))
    op.drop_table("economic_assumptions")

    with op.batch_alter_table("economic_asset_class", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_economic_asset_class_sort_order"))
        batch_op.drop_index(batch_op.f("ix_economic_asset_class_active"))
    op.drop_table("economic_asset_class")
