"""pipeline_artifacts: artefatos computacionais no banco (ADR-082)

Fase 1 do plano de migração (``_scratch/plano_migracao_artifacts_db.md``) introduz
a tabela ``pipeline_artifacts`` que substitui progressivamente os arquivos em
``storage/<ws>/processed/*.json``. Cada linha representa o output de um stage
(E2, E3, E4, E5...) para um determinado ``pipeline_run``:

- ``stage`` identifica o stage (nomes legados ``"E2"``/``"E3"``... até Fase 9;
  descritivos ``"extract_statements"``/``"reconcile_transactions"``... pós-9).
- ``artifact_key`` é o stem do documento (E2) ou nome canônico (E3+).
- ``document_id`` FK opcional: preenchido apenas em stages de extração (E2-*),
  ``NULL`` nos demais. ``ON DELETE SET NULL`` — o artefato sobrevive ao delete do
  documento (preserva histórico auditável), mas perde o vínculo.
- ``content_json`` carrega o payload do artefato (JSON/JSONB).

Constraints:
- ``UNIQUE(pipeline_run_id, stage, artifact_key)`` impede duplicação no mesmo run.
- ``INDEX(workspace_id, stage, artifact_key)`` acelera listagem por workspace.
- ``INDEX(document_id)`` acelera joins com ``documents``.

Rollback:
- ``downgrade`` faz ``DROP TABLE pipeline_artifacts`` — nenhuma outra tabela
  referencia ``pipeline_artifacts``.

Revision ID: p4q5r6s7t8u9
Revises: o3p4q5r6s7t8
Create Date: 2026-04-18
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "p4q5r6s7t8u9"
down_revision: Union[str, None] = "o3p4q5r6s7t8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "pipeline_artifacts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "workspace_id",
            sa.String(length=36),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "pipeline_run_id",
            sa.String(length=36),
            sa.ForeignKey("pipeline_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("stage", sa.String(length=50), nullable=False),
        sa.Column("artifact_key", sa.String(length=255), nullable=False),
        sa.Column(
            "document_id",
            sa.String(length=36),
            sa.ForeignKey("documents.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("content_json", sa.JSON(), nullable=False),
        sa.Column("schema_version", sa.String(length=20), nullable=True),
        sa.Column("byte_size", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.UniqueConstraint(
            "pipeline_run_id",
            "stage",
            "artifact_key",
            name="uq_pipeline_artifacts_run_stage_key",
        ),
    )
    op.create_index(
        "ix_pipeline_artifacts_workspace_id",
        "pipeline_artifacts",
        ["workspace_id"],
    )
    op.create_index(
        "ix_pipeline_artifacts_pipeline_run_id",
        "pipeline_artifacts",
        ["pipeline_run_id"],
    )
    op.create_index(
        "ix_pipeline_artifacts_workspace_stage_key",
        "pipeline_artifacts",
        ["workspace_id", "stage", "artifact_key"],
    )
    op.create_index(
        "ix_pipeline_artifacts_document_id",
        "pipeline_artifacts",
        ["document_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_pipeline_artifacts_document_id", table_name="pipeline_artifacts"
    )
    op.drop_index(
        "ix_pipeline_artifacts_workspace_stage_key", table_name="pipeline_artifacts"
    )
    op.drop_index(
        "ix_pipeline_artifacts_pipeline_run_id", table_name="pipeline_artifacts"
    )
    op.drop_index(
        "ix_pipeline_artifacts_workspace_id", table_name="pipeline_artifacts"
    )
    op.drop_table("pipeline_artifacts")
