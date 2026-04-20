"""workspace: coluna use_db_artifacts_override para opt-in por workspace (ADR-106 · A6b)

Adiciona `use_db_artifacts_override BOOLEAN NULL` em `workspaces`:
- NULL   → usa flag global `MATHOMS_USE_DB_ARTIFACTS` (comportamento existente).
- TRUE   → força `DBArtifactStore` neste workspace, mesmo com flag global FALSE.
- FALSE  → força `DiskArtifactStore` neste workspace, mesmo com flag global TRUE.

Permite ativar o modo DB artefato de forma gradual por workspace (piloto) antes
do cutover global (A6c). Rollback é um simples DROP COLUMN — sem perda de dados.

Revision ID: r6s7t8u9v0w1
Revises: q5r6s7t8u9v0
Create Date: 2026-04-19
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "r6s7t8u9v0w1"
down_revision: Union[str, None] = "q5r6s7t8u9v0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("workspaces") as batch_op:
        batch_op.add_column(
            sa.Column(
                "use_db_artifacts_override",
                sa.Boolean(),
                nullable=True,
                server_default=sa.text("NULL"),
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("workspaces") as batch_op:
        batch_op.drop_column("use_db_artifacts_override")
