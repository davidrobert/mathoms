"""adr-224 asset_catalog + workspace_asset_overrides + seed v1 (A12 · FU-2). Revision ID: adr224assetcatalog. Revises: adr222imoveisif. Create Date: 2026-05-19."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence, Union

import sqlalchemy as sa
import yaml
from alembic import context, op

revision: str = "adr224assetcatalog"
down_revision: Union[str, None] = "adr222imoveisif"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Path absoluto do seed v1 — resolvido em runtime de migration.
# Repo root é parent de backend/.
_SEED_PATH = Path(__file__).resolve().parents[3] / "config" / "asset_catalog_seed_v1.yaml"


def _load_seed_v1() -> list[dict[str, Any]]:
    """Carrega rows do YAML v1. Falha cedo se arquivo ausente."""
    if not _SEED_PATH.exists():
        raise RuntimeError(f"seed v1 ausente em {_SEED_PATH}; cutover quebra sem ele (ADR-224 §3).")
    payload = yaml.safe_load(_SEED_PATH.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("catalog_version") != 1:
        raise RuntimeError(f"seed v1 malformado (catalog_version != 1): {payload!r}")
    assets = payload.get("assets") or []
    if not isinstance(assets, list) or not assets:
        raise RuntimeError("seed v1 sem assets — V1 não pode nascer vazio")
    return assets


def _create_asset_catalog_table() -> None:
    op.create_table(
        "asset_catalog",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("catalog_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("ticker", sa.String(length=12), nullable=True),
        sa.Column("cnpj", sa.String(length=20), nullable=True),
        sa.Column("match_keyword", sa.String(length=200), nullable=True),
        sa.Column("asset_class", sa.String(length=40), nullable=False),
        sa.Column("lastro_moeda", sa.String(length=8), nullable=False),
        sa.Column("lastro_source", sa.String(length=20), nullable=False, server_default="catalog"),
        sa.Column("notes", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "lastro_moeda IN ('BRL','USD','EUR','MIXED','OTHER')",
            name="chk_asset_catalog_lastro_moeda",
        ),
        sa.CheckConstraint(
            "ticker IS NOT NULL OR cnpj IS NOT NULL OR match_keyword IS NOT NULL",
            name="chk_asset_catalog_match_at_least_one",
        ),
    )
    with op.batch_alter_table("asset_catalog", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_asset_catalog_catalog_version"),
            ["catalog_version"],
            unique=False,
        )
        batch_op.create_index(batch_op.f("ix_asset_catalog_ticker"), ["ticker"], unique=False)
        batch_op.create_index(batch_op.f("ix_asset_catalog_cnpj"), ["cnpj"], unique=False)
        batch_op.create_index(
            "uq_asset_catalog_ticker_v",
            ["catalog_version", "ticker"],
            unique=True,
            postgresql_where=sa.text("ticker IS NOT NULL"),
            sqlite_where=sa.text("ticker IS NOT NULL"),
        )
        batch_op.create_index(
            "uq_asset_catalog_cnpj_v",
            ["catalog_version", "cnpj"],
            unique=True,
            postgresql_where=sa.text("cnpj IS NOT NULL"),
            sqlite_where=sa.text("cnpj IS NOT NULL"),
        )


def _create_workspace_asset_overrides_table() -> None:
    op.create_table(
        "workspace_asset_overrides",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("asset_match_key", sa.String(length=200), nullable=False),
        sa.Column("match_kind", sa.String(length=20), nullable=False),
        sa.Column("lastro_moeda", sa.String(length=8), nullable=False),
        sa.Column(
            "override_source", sa.String(length=20), nullable=False, server_default="user_manual"
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by_user_id", sa.String(length=36), nullable=True),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "workspace_id",
            "match_kind",
            "asset_match_key",
            name="uq_ws_asset_override_ws_kind_key",
        ),
        sa.CheckConstraint(
            "lastro_moeda IN ('BRL','USD','EUR','MIXED','OTHER')",
            name="chk_ws_asset_override_lastro",
        ),
    )
    with op.batch_alter_table("workspace_asset_overrides", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_workspace_asset_overrides_workspace_id"),
            ["workspace_id"],
            unique=False,
        )


def _seed_v1_atomic() -> None:
    if context.is_offline_mode():
        op.execute("-- ADR-224 seed v1 skipped in offline mode; run via online migration.")
        return
    catalog_table = sa.table(
        "asset_catalog",
        sa.column("id", sa.String),
        sa.column("catalog_version", sa.Integer),
        sa.column("ticker", sa.String),
        sa.column("cnpj", sa.String),
        sa.column("match_keyword", sa.String),
        sa.column("asset_class", sa.String),
        sa.column("lastro_moeda", sa.String),
        sa.column("lastro_source", sa.String),
        sa.column("notes", sa.String),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    now = datetime.now(timezone.utc)
    rows = [
        {
            "id": str(uuid.uuid4()),
            "catalog_version": 1,
            "ticker": item.get("ticker"),
            "cnpj": item.get("cnpj"),
            "match_keyword": item.get("match_keyword"),
            "asset_class": item["asset_class"],
            "lastro_moeda": item["lastro_moeda"],
            "lastro_source": item.get("lastro_source", "catalog"),
            "notes": item.get("notes"),
            "created_at": now,
            "updated_at": now,
        }
        for item in _load_seed_v1()
    ]
    op.bulk_insert(catalog_table, rows)


def upgrade() -> None:
    _create_asset_catalog_table()
    _create_workspace_asset_overrides_table()
    _seed_v1_atomic()


def downgrade() -> None:
    with op.batch_alter_table("workspace_asset_overrides", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_workspace_asset_overrides_workspace_id"))
    op.drop_table("workspace_asset_overrides")

    with op.batch_alter_table("asset_catalog", schema=None) as batch_op:
        batch_op.drop_index("uq_asset_catalog_cnpj_v")
        batch_op.drop_index("uq_asset_catalog_ticker_v")
        batch_op.drop_index(batch_op.f("ix_asset_catalog_cnpj"))
        batch_op.drop_index(batch_op.f("ix_asset_catalog_ticker"))
        batch_op.drop_index(batch_op.f("ix_asset_catalog_catalog_version"))
    op.drop_table("asset_catalog")
