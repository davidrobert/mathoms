"""ADR-188 A12 P3 PR1: schema evolution learning loop (revision a2b3c4d5e6f7)."""

# Revision ID: a2b3c4d5e6f7
# Revises: f7g8h9i0j1k2
# Create Date: 2026-05-11
#
# Supersedure parcial de ADR-186 §D3/§D6 (ver ADR-188). Mudanças atômicas:
# 1. ``transaction_overrides.deleted_at`` (§D1) + partial unique
#    ``uq_txov_active_rule`` (§D2 race protection) + view
#    ``transaction_overrides_active`` (não-materializada — ADR-188 §5).
# 2. ``categorization_rules`` ganha ``deleted_at`` (§D1) + rename
#    ``revert_count`` → ``revert_count_manual_edit`` (§D3 KPI "regra
#    ruim") + ``revert_count_rule_disabled`` (§D3 abandono).
# 3. ``categorization_rules`` partial unique
#    ``uq_categorization_rule_workspace_keyword_target_active`` —
#    idempotência DB-side de POST /rules pós-soft-delete.
# 4. ``workspaces.rule_cap_override`` (§D6 consultor B2B2C cap override).
#
# Decisões em PR1 (documentadas para revisores):
# - Índice usa ``keyword`` direto (não ``keyword_normalized`` mencionado
#   em §D2). Adapter aplica uppercase ao ler; coluna nova fica para PR2
#   se UX exigir case-folded.
# - View normal (CREATE VIEW), não materializada — SQLite não suporta
#   MATERIALIZED VIEW; Postgres exigiria REFRESH manual. View normal é
#   compatível em ambos e suficiente para read volume esperado.

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a2b3c4d5e6f7"
down_revision: Union[str, Sequence[str], None] = "f7g8h9i0j1k2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_FK_RULE_ID_NAME = "fk_transaction_overrides_rule_id"


def _txov_common_columns() -> list[sa.Column]:
    """Colunas estáveis de ``transaction_overrides`` (pré/pós-PR1)."""
    return [
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.String(length=36),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("transaction_hash", sa.String(length=64), nullable=False, index=True),
        sa.Column("original_category", sa.String(length=255), nullable=False),
        sa.Column("new_category", sa.String(length=255), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("reviewed", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "source",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'manual'"),
        ),
        sa.Column(
            "rule_id",
            sa.String(length=36),
            sa.ForeignKey(
                "categorization_rules.id",
                ondelete="SET NULL",
                name=_FK_RULE_ID_NAME,
            ),
            nullable=True,
        ),
    ]


def _txov_table_pre() -> sa.Table:
    """Snapshot pré-PR1 — sem ``deleted_at``."""
    md = sa.MetaData()
    return sa.Table(
        "transaction_overrides",
        md,
        *_txov_common_columns(),
        sa.UniqueConstraint("workspace_id", "transaction_hash", name="uq_override_ws_hash"),
    )


def _txov_table_post() -> sa.Table:
    """Snapshot pós-PR1 — com ``deleted_at``."""
    md = sa.MetaData()
    return sa.Table(
        "transaction_overrides",
        md,
        *_txov_common_columns(),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("workspace_id", "transaction_hash", name="uq_override_ws_hash"),
    )


def _catrules_common_columns_pre() -> list[sa.Column]:
    """Snapshot ``categorization_rules`` pré-PR1 — com ``revert_count`` legado."""
    return [
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.String(length=36),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("keyword", sa.String(length=255), nullable=False),
        sa.Column("target_category", sa.String(length=255), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False, server_default=sa.text("100")),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("origin_override_id", sa.String(length=36), nullable=True),
        sa.Column(
            "created_by_user_id",
            sa.String(length=36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("applied_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("revert_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
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
    ]


def _catrules_table_pre() -> sa.Table:
    md = sa.MetaData()
    return sa.Table(
        "categorization_rules",
        md,
        *_catrules_common_columns_pre(),
        sa.UniqueConstraint(
            "workspace_id",
            "keyword",
            "target_category",
            name="uq_cat_rules_ws_keyword_target",
        ),
    )


def _catrules_common_columns_post() -> list[sa.Column]:
    """Snapshot ``categorization_rules`` pós-PR1 — rename + new cols."""
    return [
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.String(length=36),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("keyword", sa.String(length=255), nullable=False),
        sa.Column("target_category", sa.String(length=255), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False, server_default=sa.text("100")),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("origin_override_id", sa.String(length=36), nullable=True),
        sa.Column(
            "created_by_user_id",
            sa.String(length=36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("applied_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "revert_count_manual_edit",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "revert_count_rule_disabled",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
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
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    ]


def _catrules_table_post() -> sa.Table:
    md = sa.MetaData()
    return sa.Table(
        "categorization_rules",
        md,
        *_catrules_common_columns_post(),
        sa.UniqueConstraint(
            "workspace_id",
            "keyword",
            "target_category",
            name="uq_cat_rules_ws_keyword_target",
        ),
    )


_VIEW_TXOV_ACTIVE_SQL = """
CREATE VIEW transaction_overrides_active AS
SELECT id, workspace_id, transaction_hash, original_category, new_category,
       notes, reviewed, source, rule_id, created_at, deleted_at
FROM transaction_overrides
WHERE deleted_at IS NULL
"""


def _upgrade_txov_soft_delete() -> None:
    """transaction_overrides.deleted_at + partial unique + view (§D1, §D2)."""
    with op.batch_alter_table("transaction_overrides", copy_from=_txov_table_pre()) as batch_op:
        batch_op.add_column(sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index(
        "uq_txov_active_rule",
        "transaction_overrides",
        ["workspace_id", "transaction_hash"],
        unique=True,
        sqlite_where=sa.text("source = 'rule' AND deleted_at IS NULL"),
        postgresql_where=sa.text("source = 'rule' AND deleted_at IS NULL"),
    )
    op.execute(_VIEW_TXOV_ACTIVE_SQL)


def _upgrade_catrules_alter_table() -> None:
    """Rename + add ``deleted_at`` + add ``revert_count_rule_disabled``."""
    with op.batch_alter_table("categorization_rules", copy_from=_catrules_table_pre()) as batch_op:
        batch_op.alter_column("revert_count", new_column_name="revert_count_manual_edit")
        rev_disabled = sa.Column(
            "revert_count_rule_disabled",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        )
        batch_op.add_column(rev_disabled)
        batch_op.add_column(sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))


def _upgrade_catrules_evolution() -> None:
    """categorization_rules rename + add cols + partial unique (§D1, §D2, §D3)."""
    _upgrade_catrules_alter_table()
    op.create_index(
        "uq_categorization_rule_workspace_keyword_target_active",
        "categorization_rules",
        ["workspace_id", "keyword", "target_category"],
        unique=True,
        sqlite_where=sa.text("deleted_at IS NULL"),
        postgresql_where=sa.text("deleted_at IS NULL"),
    )


def _upgrade_workspaces_cap_override() -> None:
    """workspaces.rule_cap_override (§D6 B2B2C cap override)."""
    with op.batch_alter_table("workspaces", schema=None) as batch_op:
        batch_op.add_column(sa.Column("rule_cap_override", sa.Integer(), nullable=True))


def upgrade() -> None:
    """Apply ADR-188 schema delta."""
    _upgrade_txov_soft_delete()
    _upgrade_catrules_evolution()
    _upgrade_workspaces_cap_override()


def _downgrade_workspaces_cap_override() -> None:
    with op.batch_alter_table("workspaces", schema=None) as batch_op:
        batch_op.drop_column("rule_cap_override")


def _downgrade_catrules_evolution() -> None:
    op.drop_index(
        "uq_categorization_rule_workspace_keyword_target_active",
        table_name="categorization_rules",
    )
    with op.batch_alter_table("categorization_rules", copy_from=_catrules_table_post()) as batch_op:
        batch_op.drop_column("deleted_at")
        batch_op.drop_column("revert_count_rule_disabled")
        batch_op.alter_column("revert_count_manual_edit", new_column_name="revert_count")


def _downgrade_txov_soft_delete() -> None:
    op.execute("DROP VIEW IF EXISTS transaction_overrides_active")
    op.execute("DROP INDEX IF EXISTS uq_txov_active_rule")
    with op.batch_alter_table("transaction_overrides", copy_from=_txov_table_post()) as batch_op:
        batch_op.drop_column("deleted_at")


def downgrade() -> None:
    """Revert ADR-188 schema delta."""
    _downgrade_workspaces_cap_override()
    _downgrade_catrules_evolution()
    _downgrade_txov_soft_delete()
