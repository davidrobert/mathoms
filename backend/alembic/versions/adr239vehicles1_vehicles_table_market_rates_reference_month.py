"""ADR-239 (A18 L1 P1): tabela vehicles + market_rates.reference_month.

Revision ID: adr239vehicles1
Revises: adr238informes2
Create Date: 2026-05-21

Cria a tabela canônica ``vehicles`` (ADR-239 D1) com identidade imutável
``(workspace_id, placa)`` + CHECK constraint para RENAVAM length. Adiciona
``market_rates.reference_month`` (formato 'YYYY-MM') para reconciliação
de cotações FIPE mensais (ADR-239 D7, gancho para A18 L3).

Mudanças
--------
1. **`vehicles` table** — schema cf. ADR-239 §D1 Implementação. UNIQUE
   ``(workspace_id, placa)`` + CHECK ``length(renavam) BETWEEN 9 AND 11``
   (regex completo `^[0-9]{9,11}$` validado em Pydantic boundary P2).
   CHECK ``codigo_rfb IN ('21', '22', '23')`` para invariante ADR-225.
2. **`market_rates.reference_month TEXT NULL`** — capturar mês FIPE
   (ex.: ``'2026-05'``); nullable porque PTAX diário não usa.

Rollback
--------
Postgres + SQLite: ``DROP TABLE vehicles`` é destrutivo mas seguro pois
nenhum FK aponta para vehicles (projection em
``baseline_patrimonial.veiculos_consolidados[]`` é JSON, não FK). Coluna
``reference_month`` simples drop.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import MetaData, Table

revision: str = "adr239vehicles1"
down_revision: Union[str, Sequence[str], None] = "adr238informes2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _market_rates_pre() -> Table:
    """Snapshot pré-ADR-239 (sem reference_month) — habilita batch_alter_table em SQLite --sql."""
    return Table(
        "market_rates",
        MetaData(),
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("pair", sa.String(16), nullable=False),
        sa.Column("rate", sa.Numeric(20, 10), nullable=False),
        sa.Column("observed_at", sa.Date(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def _market_rates_post() -> Table:
    """Snapshot pós-ADR-239 (com reference_month) — habilita batch_alter_table no downgrade."""
    return Table(
        "market_rates",
        MetaData(),
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("pair", sa.String(16), nullable=False),
        sa.Column("rate", sa.Numeric(20, 10), nullable=False),
        sa.Column("observed_at", sa.Date(), nullable=False),
        sa.Column("reference_month", sa.String(7), nullable=True),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


_NOW = sa.text("CURRENT_TIMESTAMP")


def _vehicles_id_workspace_cols() -> list[sa.Column]:
    return [
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.String(36),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
    ]


def _vehicles_payload_cols() -> list[sa.Column]:
    return [
        sa.Column("placa", sa.String(10), nullable=False),
        sa.Column("renavam", sa.String(11), nullable=False),
        sa.Column("marca", sa.String(60), nullable=False),
        sa.Column("modelo", sa.String(120), nullable=False),
        sa.Column("ano_modelo", sa.Integer(), nullable=False),
        sa.Column("ano_fabricacao", sa.Integer(), nullable=False),
        sa.Column("fipe_code", sa.String(20), nullable=True),
        sa.Column("cor", sa.String(30), nullable=True),
        sa.Column("combustivel", sa.String(20), nullable=True),
        sa.Column("codigo_rfb", sa.String(4), nullable=False, server_default="21"),
    ]


def _vehicles_audit_cols() -> list[sa.Column]:
    return [
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=_NOW),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=_NOW),
    ]


def _vehicles_columns() -> list[sa.Column]:
    return [*_vehicles_id_workspace_cols(), *_vehicles_payload_cols(), *_vehicles_audit_cols()]


def _vehicles_constraints() -> list:
    return [
        sa.UniqueConstraint("workspace_id", "placa", name="uq_workspace_placa"),
        sa.CheckConstraint(
            "length(renavam) BETWEEN 9 AND 11",
            name="chk_vehicles_renavam_length",
        ),
        sa.CheckConstraint(
            "codigo_rfb IN ('21', '22', '23')",
            name="chk_vehicles_codigo_rfb",
        ),
    ]


def upgrade() -> None:
    """Cria vehicles + adiciona market_rates.reference_month."""
    op.create_table("vehicles", *_vehicles_columns(), *_vehicles_constraints())
    # market_rates.reference_month — gancho para FIPE refresh em A18 L3.
    with op.batch_alter_table("market_rates", copy_from=_market_rates_pre()) as batch:
        batch.add_column(
            sa.Column("reference_month", sa.String(7), nullable=True, server_default=None)
        )


def downgrade() -> None:
    """Drop vehicles + remove market_rates.reference_month (tolerante a ausência)."""
    op.drop_table("vehicles")

    try:
        with op.batch_alter_table("market_rates", copy_from=_market_rates_post()) as batch:
            batch.drop_column("reference_month")
    except (ValueError, Exception):
        pass
