"""adr-131 report analysis_artifact_id

Revision ID: v0w1x2y3z4a5
Revises: u9v0w1x2y3z4
Create Date: 2026-04-25

ADR-131: substitui ``reports.analysis_json_path`` (path filesystem) por
``analysis_artifact_id`` (FK direto para ``pipeline_artifacts.id``). O
relatório passa a ler ``content_json`` do DB; nenhum filesystem nesse
caminho. ``size_bytes`` também sai (calculado on-the-fly do payload
quando precisar).

Backfill durante upgrade:
    UPDATE reports
    SET analysis_artifact_id = (SELECT id FROM pipeline_artifacts pa
        WHERE pa.pipeline_run_id = reports.pipeline_run_id
          AND pa.stage = 'E5'
          AND pa.artifact_key = 'analise_financeira'
        LIMIT 1)

Reports sem ``pipeline_run_id`` ou cujo run não tem o artefato no DB
ficam com ``analysis_artifact_id = NULL`` — endpoint
``GET /reports/{id}/data`` retorna 404, mesma UX de quando hoje o
arquivo de disco não existe.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "v0w1x2y3z4a5"
down_revision: Union[str, None] = "u9v0w1x2y3z4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_FK_NAME = "fk_reports_analysis_artifact_id"


def _common_columns() -> list[sa.Column]:
    """Colunas que NÃO mudam (compartilhadas pelos snapshots pré/intermediário/pós)."""
    return [
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("workspace_id", sa.String(36), nullable=False),
        sa.Column("pipeline_run_id", sa.String(36), nullable=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("period", sa.String(50), nullable=True),
        sa.Column("tasks_snapshot_json", sa.JSON(), nullable=True),
        sa.Column("premissas_snapshot_json", sa.JSON(), nullable=True),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("patrimonio_liquido", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    ]


def _artifact_fk_column() -> sa.Column:
    return sa.Column(
        "analysis_artifact_id",
        sa.Integer(),
        sa.ForeignKey("pipeline_artifacts.id", ondelete="SET NULL", name=_FK_NAME),
        nullable=True,
    )


def _table_pre() -> sa.Table:
    """Schema antes do upgrade — analysis_json_path + size_bytes, sem FK."""
    md = sa.MetaData()
    return sa.Table(
        "reports",
        md,
        *_common_columns(),
        sa.Column("analysis_json_path", sa.Text(), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
    )


def _table_intermediate() -> sa.Table:
    """Schema durante upgrade após passo 1 — colunas antigas + nova + FK."""
    md = sa.MetaData()
    return sa.Table(
        "reports",
        md,
        *_common_columns(),
        sa.Column("analysis_json_path", sa.Text(), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        _artifact_fk_column(),
    )


def _table_post() -> sa.Table:
    """Schema após upgrade — só analysis_artifact_id (com FK)."""
    md = sa.MetaData()
    return sa.Table(
        "reports",
        md,
        *_common_columns(),
        _artifact_fk_column(),
    )


def upgrade() -> None:
    # 1) Adiciona coluna nova + FK; preserva analysis_json_path e size_bytes.
    with op.batch_alter_table("reports", copy_from=_table_pre()) as batch_op:
        batch_op.add_column(_artifact_fk_column())

    # 2) Backfill: para cada Report com pipeline_run_id, achar o artifact
    #    E5/analise_financeira do mesmo run e setar a FK.
    op.execute(
        """
        UPDATE reports
        SET analysis_artifact_id = (
            SELECT pa.id FROM pipeline_artifacts pa
            WHERE pa.pipeline_run_id = reports.pipeline_run_id
              AND pa.stage = 'E5'
              AND pa.artifact_key = 'analise_financeira'
            LIMIT 1
        )
        WHERE reports.pipeline_run_id IS NOT NULL
        """
    )

    # 3) Drop colunas obsoletas; FK declarada no snapshot intermediário
    #    para que SQLite preserve a constraint ao rebuildar a tabela.
    with op.batch_alter_table("reports", copy_from=_table_intermediate()) as batch_op:
        batch_op.drop_column("analysis_json_path")
        batch_op.drop_column("size_bytes")


def downgrade() -> None:
    # Restaura colunas (NÃO o dado — analysis_json_path fica NULL).
    with op.batch_alter_table("reports", copy_from=_table_post()) as batch_op:
        batch_op.add_column(sa.Column("analysis_json_path", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("size_bytes", sa.Integer(), nullable=True))
        batch_op.drop_constraint(_FK_NAME, type_="foreignkey")
        batch_op.drop_column("analysis_artifact_id")
