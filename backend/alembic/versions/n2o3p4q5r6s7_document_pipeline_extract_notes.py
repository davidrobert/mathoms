"""documents: add pipeline_extract_notes column

Stores newline-separated notes from the E2 extract JSON (notas[] field).
Populated by document_pipeline_sync after each pipeline run so the listing
can surface extraction errors without reading JSON files per request.

Revision ID: n2o3p4q5r6s7
Revises: m1n2o3p4q5r6
Create Date: 2026-04-18
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "n2o3p4q5r6s7"
down_revision: Union[str, None] = "m1n2o3p4q5r6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("pipeline_extract_notes", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("documents", "pipeline_extract_notes")
