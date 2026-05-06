"""ADR-165 onda 2 — stage_reviews.validation_issues JSON nullable.

Revision ID: f2b3c4d5e6a7
Revises: c3d4e5f6a7b8
Create Date: 2026-05-06

Adiciona coluna `validation_issues: JSON nullable` para issues estruturadas
(code/severity/path/context/legacy_message). Reviews pré-cutover ficam com
NULL — UI faz fallback para `validation_errors: Text` legacy. `summary` é
derived no DTO (ADR-165 D4), não persistido.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f2b3c4d5e6a7"
down_revision: Union[str, None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("stage_reviews") as batch_op:
        batch_op.add_column(sa.Column("validation_issues", sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("stage_reviews") as batch_op:
        batch_op.drop_column("validation_issues")
