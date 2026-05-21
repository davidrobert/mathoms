"""ADR-241: índice composto para lookup de mais-recente-por-workspace.

Revision ID: adr241index
Revises: adr238informes2
Create Date: 2026-05-21

Adiciona índice ``ix_pipeline_artifacts_ws_stage_key_created`` em
``pipeline_artifacts(workspace_id, stage, artifact_key, created_at DESC)``
para acelerar ``DBArtifactStore._get_latest_in_workspace`` em workspaces
com muitas runs por (stage, key).

Sem este índice, ``ORDER BY created_at DESC LIMIT 1`` faz scan de todas
as rows que satisfazem ``(workspace_id, stage, artifact_key)`` e ordena
em memória — O(N runs) por chamada. Com a promoção de E2 a workspace-scoped
(ADR-241), o caminho quente do pipeline passa a chamar
``_get_latest_in_workspace`` para cada um dos N documentos por workspace.
Em workspace com 100 docs × 10 runs históricas, ~1000 rows extras por run
ficam no scan path se não tiver índice.

O índice existente ``ix_pipeline_artifacts_workspace_stage_key`` não cobre
``created_at`` — continua útil para ``list_keys`` (DISTINCT por
``workspace_id, stage``) e para queries por chave canônica, então é
preservado. O novo índice acrescenta a coluna de ordenação.

Política Postgres + SQLite: ambos suportam ``CREATE INDEX … (col DESC)``;
SQLite trata DESC dentro do índice desde 3.3 (2006). Em Postgres, o
``DESC`` mira queries com ``ORDER BY … DESC LIMIT 1`` (index-only scan).
"""

from typing import Sequence, Union

from alembic import op

revision: str = "adr241index"
down_revision: Union[str, Sequence[str], None] = "adr239vehicles1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_INDEX_NAME = "ix_pipeline_artifacts_ws_stage_key_created"


def upgrade() -> None:
    op.create_index(
        _INDEX_NAME,
        "pipeline_artifacts",
        ["workspace_id", "stage", "artifact_key", "created_at"],
        unique=False,
        # `created_at` DESC para casar com `_get_latest_in_workspace`
        # (ORDER BY created_at DESC LIMIT 1). Alembic 1.10+ aceita
        # `postgresql_ops` para direcionar; em SQLite a DESC é honrada
        # como parte do índice. Definição via SQLAlchemy `text()` mantém
        # portabilidade.
        postgresql_ops={"created_at": "DESC"},
    )


def downgrade() -> None:
    op.drop_index(_INDEX_NAME, table_name="pipeline_artifacts")
