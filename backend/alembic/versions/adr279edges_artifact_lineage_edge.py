"""ADR-279 (revision adr279edges, revises a170rtf00001) — tabela derivada
``artifact_lineage_edge`` (índice reverso field-level do ``_lineage`` E5, A25.l3).
Retenção N=1 por workspace (B6): writer faz DELETE+INSERT atômico no hook pós-run;
tabela rebuildável, nunca fonte primária. FKs portáveis (workspaces/pipeline_runs/
documents) inline no ``create_table`` (precedente adr278datasource — SQLite aceita o
DDL sem enforcement); FK ``data_source_id`` → ``data_source`` é Postgres-only via
``ADD CONSTRAINT`` (tabela nasce vazia → instantâneo; padrão adr278datasourcefk,
model mantém coluna plain). Índices ``(workspace_id, run_id)`` (load-bearing p/ o
DELETE de retenção) e ``(workspace_id, source_document_id)`` (query reversa) via
``CREATE INDEX CONCURRENTLY`` fora de transação no Postgres (``autocommit_block``);
índice ``(workspace_id, rule_ref)`` deferido com o MCP (coluna sim, índice não).
Runbook: ``docs/reference/runbooks/data_lineage_migrations.md`` §Fase E."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "adr279edges"
down_revision: Union[str, Sequence[str], None] = "a170rtf00001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLE = "artifact_lineage_edge"
_IX_WS_RUN = "ix_artifact_lineage_edge_ws_run"
_IX_WS_DOC = "ix_artifact_lineage_edge_ws_doc"
_FK_DATA_SOURCE = "fk_artifact_lineage_edge_data_source_id"


def _is_postgres() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def _create_table() -> None:
    op.create_table(
        _TABLE,
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "workspace_id",
            sa.String(length=36),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "run_id",
            sa.String(length=36),
            sa.ForeignKey("pipeline_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("src_stage", sa.String(length=50), nullable=False),
        sa.Column("src_key", sa.String(length=255), nullable=False),
        sa.Column("src_field", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("dst_stage", sa.String(length=50), nullable=False),
        sa.Column("dst_key", sa.String(length=255), nullable=False),
        sa.Column("dst_field", sa.String(length=255), nullable=False),
        sa.Column("edge_type", sa.String(length=32), nullable=False),
        sa.Column("rule_ref", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "source_document_id",
            sa.String(length=36),
            sa.ForeignKey("documents.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("data_source_id", sa.String(length=36), nullable=True),
        sa.Column("winner", sa.Boolean(), nullable=False, server_default=sa.true()),
    )


def _create_indexes() -> None:
    columns = {
        _IX_WS_RUN: ["workspace_id", "run_id"],
        _IX_WS_DOC: ["workspace_id", "source_document_id"],
    }
    if not _is_postgres():
        for name, cols in columns.items():
            op.create_index(name, _TABLE, cols)
        return
    # CONCURRENTLY exige rodar fora de transação (autocommit_block comita a corrente).
    with op.get_context().autocommit_block():
        for name, cols in columns.items():
            op.create_index(name, _TABLE, cols, postgresql_concurrently=True)


def upgrade() -> None:
    _create_table()
    if _is_postgres():
        # Tabela vazia → ADD CONSTRAINT valida instantâneo (sem NOT VALID/VALIDATE).
        op.execute(
            f"ALTER TABLE {_TABLE} ADD CONSTRAINT {_FK_DATA_SOURCE} "
            "FOREIGN KEY (data_source_id) REFERENCES data_source (id) ON DELETE SET NULL"
        )
    _create_indexes()


def downgrade() -> None:
    op.drop_table(_TABLE)
