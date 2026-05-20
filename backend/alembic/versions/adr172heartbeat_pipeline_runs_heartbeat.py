"""ADR-172: pipeline_runs.last_heartbeat_at + failure_reason (W2-T04).

Adiciona infraestrutura de stuck-runs detector:

- ``last_heartbeat_at TIMESTAMP NULL`` — atualizado em stage start; beat
  task ``fin.detect_stuck_runs`` (5min) marca runs com heartbeat estale
  como ``failed`` com ``failure_reason='heartbeat_timeout'``.
- ``failure_reason VARCHAR(50) NULL`` — taxonomia aberta de motivos de
  falha (vocabulário começa com ``heartbeat_timeout``; cresce sem
  migration via ``backend/app/services/pipeline_failure_reasons.py``).
- Partial index ``ix_pipeline_runs_running_heartbeat`` — beat task scan
  só toca rows ``status='running'`` (cardinalidade baixa em prod).
- Backfill ``last_heartbeat_at = started_at`` em runs ``running`` no
  deploy — evita janela cega onde runs em voo ficam invisíveis ao
  detector (recomendação data-engineer + sre-devops review).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "adr172heartbeat"
down_revision: Union[str, Sequence[str], None] = "adr229irpfprefill"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("pipeline_runs") as batch:
        batch.add_column(sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("failure_reason", sa.String(length=50), nullable=True))

    op.create_index(
        "ix_pipeline_runs_running_heartbeat",
        "pipeline_runs",
        ["last_heartbeat_at"],
        postgresql_where=sa.text("status='running'"),
        sqlite_where=sa.text("status='running'"),
    )

    op.execute(
        "UPDATE pipeline_runs SET last_heartbeat_at = started_at "
        "WHERE status = 'running' AND last_heartbeat_at IS NULL"
    )


def downgrade() -> None:
    op.drop_index("ix_pipeline_runs_running_heartbeat", table_name="pipeline_runs")
    with op.batch_alter_table("pipeline_runs") as batch:
        batch.drop_column("failure_reason")
        batch.drop_column("last_heartbeat_at")
