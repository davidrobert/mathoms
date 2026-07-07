"""A32.l5 — coluna prompt_version em pipeline_artifacts (ADR-311).

Revision ID: a32l5promptver
Revises: a31l1opsaudit
Create Date: 2026-07-07

Versão de extração (PROMPT_VERSION do writer LLM, já presente no payload
desde ADR-233/W2-T05) vira coluna consultável — habilita o script dirigido
de re-extração (``dev/reextract_stale_e2_llm.py``). Migration leve por
decisão da ADR-311 D4: rows existentes ficam NULL ≡ versão desconhecida/0;
sem backfill de conteúdo (payload é Fernet-encrypted at-rest, ADR-231 —
backfill exigiria decrypt em massa). Writes novos populam a coluna via
lift do payload em ``DBArtifactStore.write``.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a32l5promptver"
down_revision: Union[str, Sequence[str], None] = "a31l1opsaudit"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "pipeline_artifacts",
        sa.Column("prompt_version", sa.String(20), nullable=True),
    )


def downgrade() -> None:
    with op.batch_alter_table("pipeline_artifacts") as batch_op:
        batch_op.drop_column("prompt_version")
