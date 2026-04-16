"""pipeline_runs: partial unique index — single active run per workspace (ADR-072 · P0.3)

Prevents race condition where two concurrent `POST /pipeline/run` requests
pass the "no active run" check and both insert a PipelineRun. The partial
unique index on `(workspace_id)` filtered by `status IN ('pending', 'running')`
rejects the 2nd INSERT with IntegrityError — the API layer converts that to 409.

Works on both SQLite (3.8+) and Postgres (partial indexes with WHERE clause
are supported since MVCC-era). Dropping the index reverts to the app-level
count check (which has the race).

Revision ID: i4c5d6e7f8a9
Revises: h3b4c5d6e7f8
Create Date: 2026-04-16
"""

from typing import Sequence, Union

from alembic import op


revision: str = "i4c5d6e7f8a9"
down_revision: Union[str, Sequence[str], None] = "h3b4c5d6e7f8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Partial unique index — at most one pipeline_run per workspace
    # can be in 'pending' or 'running' status at any given time.
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ux_pipeline_runs_ws_active
        ON pipeline_runs (workspace_id)
        WHERE status IN ('pending', 'running')
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ux_pipeline_runs_ws_active")
