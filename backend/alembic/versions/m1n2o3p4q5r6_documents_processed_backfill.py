"""documents: backfill status processed quando já houve pipeline (F11 UX)

Após um run bem-sucedido, ``sync_documents_pipeline_e2_status`` promove
``ready`` → ``processed``. Esta migração alinha linhas antigas que já tinham
``pipeline_last_run_at`` mas ainda ``ready``.

Revision ID: m1n2o3p4q5r6
Revises: l7f8g9h0i1j2
Create Date: 2026-04-17
"""

from typing import Sequence, Union

from alembic import op

revision: str = "m1n2o3p4q5r6"
down_revision: Union[str, None] = "l7f8g9h0i1j2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE documents
        SET status = 'processed'
        WHERE status = 'ready'
          AND pipeline_last_run_at IS NOT NULL
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE documents
        SET status = 'ready'
        WHERE status = 'processed'
          AND pipeline_last_run_at IS NOT NULL
        """
    )
