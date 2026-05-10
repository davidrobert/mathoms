"""ADR-185 §4 — workspace_category_overrides.updated_by_user_id (audit mínima).

Revision ID: a9b0c1d2e3f4
Revises: d6e7f8a9b0c1
Create Date: 2026-05-10

A11.cat-overrides-ux W2-T01: adiciona coluna nullable ``updated_by_user_id``
em ``workspace_category_overrides`` (FK ``users.id`` com ``ON DELETE SET NULL``).

Não-breaking:
- Coluna nullable; sem backfill — handlers com ``current_user`` populam daqui
  pra frente, registros existentes ficam ``NULL``.
- ``ON DELETE SET NULL`` preserva o override se o user for soft-deleted.
- Audit mínima — não substitui Decision/AuditLog event-sourced; cobre só
  "quem editou esta linha" para a UI W4.

Schema delta (ver ``backend/app/models/category_template.py``):
    workspace_category_overrides
        + updated_by_user_id VARCHAR(36) NULL  -- FK→users.id ON DELETE SET NULL

SQLite-specific (offline SQL): ``batch_alter_table`` recria a tabela; precisa
de ``copy_from`` com snapshot estático do schema pré/pós para suportar
``alembic upgrade head --sql`` (ver ``test_offline_sql_generation_works``).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a9b0c1d2e3f4"
down_revision: Union[str, Sequence[str], None] = "d6e7f8a9b0c1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_FK_NAME = "fk_ws_cat_override_updated_by_user_id"


def _common_columns() -> list[sa.Column]:
    """Colunas inalteradas — compartilhadas entre snapshots pré e pós."""
    return [
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.String(36),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("template_key", sa.String(100), nullable=False, index=True),
        sa.Column("label_override", sa.String(120), nullable=True),
        sa.Column("keywords_override", sa.JSON(), nullable=True),
        sa.Column("monthly_cap_brl_cents_override", sa.BigInteger(), nullable=True),
        sa.Column("disabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    ]


def _table_pre() -> sa.Table:
    """Snapshot pré-upgrade — sem ``updated_by_user_id``."""
    md = sa.MetaData()
    return sa.Table(
        "workspace_category_overrides",
        md,
        *_common_columns(),
        sa.UniqueConstraint("workspace_id", "template_key", name="uq_ws_cat_override_ws_key"),
    )


def _table_post() -> sa.Table:
    """Snapshot pós-upgrade — com ``updated_by_user_id`` + FK."""
    md = sa.MetaData()
    return sa.Table(
        "workspace_category_overrides",
        md,
        *_common_columns(),
        sa.Column(
            "updated_by_user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="SET NULL", name=_FK_NAME),
            nullable=True,
        ),
        sa.UniqueConstraint("workspace_id", "template_key", name="uq_ws_cat_override_ws_key"),
    )


def upgrade() -> None:
    """Add ``updated_by_user_id`` column with FK to ``users.id`` (nullable, SET NULL)."""
    with op.batch_alter_table(
        "workspace_category_overrides",
        copy_from=_table_pre(),
    ) as batch_op:
        batch_op.add_column(
            sa.Column(
                "updated_by_user_id",
                sa.String(length=36),
                sa.ForeignKey("users.id", ondelete="SET NULL", name=_FK_NAME),
                nullable=True,
            )
        )


def downgrade() -> None:
    """Drop ``updated_by_user_id`` column (FK desaparece junto na recriação)."""
    with op.batch_alter_table(
        "workspace_category_overrides",
        copy_from=_table_post(),
    ) as batch_op:
        batch_op.drop_column("updated_by_user_id")
