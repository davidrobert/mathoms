"""ADR-186 A12 P1: categorization_rules + transaction_overrides.source/rule_id."""

# Revision ID: f7g8h9i0j1k2
# Revises: a9b0c1d2e3f4
# Create Date: 2026-05-10
#
# Schema base do learning loop (ADR-186 §D3). 3 mudanças atômicas:
# 1. ``transaction_overrides.source`` VARCHAR(20) NOT NULL DEFAULT 'manual'
#    — distingue override manual de override criado pela aplicação
#    automática de regra ('rule'). Backfill via server default.
# 2. Tabela ``categorization_rules`` — agregado de regras aprendidas por
#    workspace. ``origin_override_id`` soft reference (sem FK formal —
#    evita ciclo com ``transaction_overrides.rule_id``).
# 3. ``transaction_overrides.rule_id`` NULLABLE FK para
#    ``categorization_rules.id`` (``ON DELETE SET NULL``).
#
# P1 não muda comportamento do pipeline E4 (P2 consome).
#
# SQLite-specific (offline SQL): ``batch_alter_table`` recria a tabela; precisa
# de ``copy_from`` com snapshot estático do schema pré/pós para suportar
# ``alembic upgrade head --sql`` (ver ``test_offline_sql_generation_works``).

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f7g8h9i0j1k2"
down_revision: Union[str, Sequence[str], None] = "a9b0c1d2e3f4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_FK_RULE_ID_NAME = "fk_transaction_overrides_rule_id"


def _common_columns() -> list[sa.Column]:
    """Colunas inalteradas de ``transaction_overrides`` — pré e pós."""
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
    ]


def _table_pre() -> sa.Table:
    """Snapshot pré-upgrade — sem ``source`` nem ``rule_id``."""
    md = sa.MetaData()
    return sa.Table(
        "transaction_overrides",
        md,
        *_common_columns(),
        sa.UniqueConstraint("workspace_id", "transaction_hash", name="uq_override_ws_hash"),
    )


def _table_mid() -> sa.Table:
    """Snapshot intermediário — pós-add ``source``, antes de ``rule_id``."""
    md = sa.MetaData()
    return sa.Table(
        "transaction_overrides",
        md,
        *_common_columns(),
        sa.Column(
            "source",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'manual'"),
        ),
        sa.UniqueConstraint("workspace_id", "transaction_hash", name="uq_override_ws_hash"),
    )


def _table_post() -> sa.Table:
    """Snapshot pós-upgrade — com ``source`` + ``rule_id`` + FK."""
    md = sa.MetaData()
    return sa.Table(
        "transaction_overrides",
        md,
        *_common_columns(),
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
        sa.UniqueConstraint("workspace_id", "transaction_hash", name="uq_override_ws_hash"),
    )


def upgrade() -> None:
    """Add ``source`` + ``rule_id`` to transaction_overrides; create categorization_rules."""
    # 1) transaction_overrides.source — default 'manual' cobre backfill.
    with op.batch_alter_table(
        "transaction_overrides",
        copy_from=_table_pre(),
    ) as batch_op:
        batch_op.add_column(
            sa.Column(
                "source",
                sa.String(length=20),
                nullable=False,
                server_default=sa.text("'manual'"),
            )
        )

    # 2) categorization_rules (ADR-186 §D3).
    op.create_table(
        "categorization_rules",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.String(length=36),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("keyword", sa.String(length=255), nullable=False),
        sa.Column("target_category", sa.String(length=255), nullable=False),
        sa.Column(
            "priority",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("100"),
        ),
        sa.Column(
            "enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "origin_override_id",
            sa.String(length=36),
            # FK adicionado fora do CREATE TABLE para quebrar ciclo SQLAlchemy
            # (TO.rule_id → CR.id; CR.origin_override_id → TO.id). Modelado
            # com ``use_alter=True`` — runtime equivalente.
            nullable=True,
        ),
        sa.Column(
            "created_by_user_id",
            sa.String(length=36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "applied_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "revert_count",
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
        sa.UniqueConstraint(
            "workspace_id",
            "keyword",
            "target_category",
            name="uq_cat_rules_ws_keyword_target",
        ),
    )
    op.create_index(
        "ix_categorization_rules_workspace_id",
        "categorization_rules",
        ["workspace_id"],
    )
    op.create_index(
        "ix_categorization_rules_workspace_enabled",
        "categorization_rules",
        ["workspace_id", "enabled"],
    )
    op.create_index(
        "ix_categorization_rules_workspace_keyword",
        "categorization_rules",
        ["workspace_id", "keyword"],
    )

    # 3) transaction_overrides.rule_id — FK opcional para auditoria.
    # Single batch: add_column + FK constraint (ambos exigem rebuild da
    # tabela em SQLite). Index é op separada após o batch fechar.
    with op.batch_alter_table(
        "transaction_overrides",
        copy_from=_table_mid(),
    ) as batch_op:
        batch_op.add_column(
            sa.Column(
                "rule_id",
                sa.String(length=36),
                nullable=True,
            )
        )
        batch_op.create_foreign_key(
            _FK_RULE_ID_NAME,
            "categorization_rules",
            ["rule_id"],
            ["id"],
            ondelete="SET NULL",
        )

    op.create_index(
        "ix_transaction_overrides_rule_id",
        "transaction_overrides",
        ["rule_id"],
    )


def downgrade() -> None:
    """Drop rule_id FK + categorization_rules + source column."""
    # Drop index fora de batch_alter_table — batch só pra schema ops
    # (DROP COLUMN exige recreate da tabela em SQLite). ``if_exists`` por
    # safety em DBs onde a criação anterior falhou parcialmente.
    op.execute("DROP INDEX IF EXISTS ix_transaction_overrides_rule_id")

    with op.batch_alter_table(
        "transaction_overrides",
        copy_from=_table_post(),
    ) as batch_op:
        batch_op.drop_column("rule_id")

    op.drop_index(
        "ix_categorization_rules_workspace_keyword",
        table_name="categorization_rules",
    )
    op.drop_index(
        "ix_categorization_rules_workspace_enabled",
        table_name="categorization_rules",
    )
    op.drop_index(
        "ix_categorization_rules_workspace_id",
        table_name="categorization_rules",
    )
    op.drop_table("categorization_rules")

    with op.batch_alter_table(
        "transaction_overrides",
        copy_from=_table_mid(),
    ) as batch_op:
        batch_op.drop_column("source")
