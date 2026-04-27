"""adr-137 category_templates + workspace_category_overrides + institution_catalog (A7.3)

Revision ID: aa1b2c3d4e5f
Revises: z4a5b6c7d8e9
Create Date: 2026-04-27

ADR-137 (CONFIG_CUTOVER_PLAN.md §5.3): split do agregado ``Category`` em
**template global versionado** (``category_templates``, mantido por seed
Alembic) + **overrides por workspace** (``workspace_category_overrides``,
somente diff). ``institution_catalog`` global substitui leitura de
``config/institutions.json``.

Ainda **não dropa** ``categories``/``category_keywords`` — A7.5 fará o
cleanup após backfill verde + bench. Esta migration cria as tabelas
novas; o seed do template v1 + backfill de overrides + seed do catálogo
de instituições vivem em data migrations separadas (próximas revisões).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "aa1b2c3d4e5f"
down_revision: Union[str, None] = "z4a5b6c7d8e9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "category_templates",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("template_version", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column("parent_key", sa.String(length=100), nullable=True),
        sa.Column("label", sa.String(length=120), nullable=False),
        sa.Column("category_type", sa.String(length=10), nullable=False),
        sa.Column("default_keywords", sa.JSON(), nullable=False),
        sa.Column("default_monthly_cap_brl_cents", sa.BigInteger(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("template_version", "key", name="uq_category_templates_version_key"),
    )
    with op.batch_alter_table("category_templates", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_category_templates_template_version"),
            ["template_version"],
            unique=False,
        )
        batch_op.create_index(batch_op.f("ix_category_templates_key"), ["key"], unique=False)

    op.create_table(
        "workspace_category_overrides",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("template_key", sa.String(length=100), nullable=False),
        sa.Column("label_override", sa.String(length=120), nullable=True),
        sa.Column("keywords_override", sa.JSON(), nullable=True),
        sa.Column("monthly_cap_brl_cents_override", sa.BigInteger(), nullable=True),
        sa.Column("disabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workspace_id", "template_key", name="uq_ws_cat_override_ws_key"),
    )
    with op.batch_alter_table("workspace_category_overrides", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_workspace_category_overrides_workspace_id"),
            ["workspace_id"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_workspace_category_overrides_template_key"),
            ["template_key"],
            unique=False,
        )

    op.create_table(
        "institution_catalog",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("default_parser", sa.String(length=80), nullable=True),
        sa.Column("category", sa.String(length=20), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("institution_catalog", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_institution_catalog_code"), ["code"], unique=True)


def downgrade() -> None:
    with op.batch_alter_table("institution_catalog", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_institution_catalog_code"))
    op.drop_table("institution_catalog")

    with op.batch_alter_table("workspace_category_overrides", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_workspace_category_overrides_template_key"))
        batch_op.drop_index(batch_op.f("ix_workspace_category_overrides_workspace_id"))
    op.drop_table("workspace_category_overrides")

    with op.batch_alter_table("category_templates", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_category_templates_key"))
        batch_op.drop_index(batch_op.f("ix_category_templates_template_version"))
    op.drop_table("category_templates")
