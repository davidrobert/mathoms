"""REL-03: índice único parcial (workspace_id, pipeline_run_id) em reports.

Revision ID: rel03reportuniq
Revises: adr291baserun
Create Date: 2026-06-18

Redelivery do Celery (``acks_late`` + ``reject_on_worker_lost``) reenfileira
a mensagem quando o worker morre (OOM/timeout/kill) antes do ack; o run
re-roda e ``_create_report_from_output`` insere um segundo Report para o
mesmo ``pipeline_run_id``. O índice único parcial transforma o duplicado em
``IntegrityError`` capturável — defesa no nível do banco, independente de
corrida entre workers.

Parcial em ``WHERE pipeline_run_id IS NOT NULL``: a coluna é nullable
(``ON DELETE SET NULL`` quando o run é hard-deleted), e Reports órfãos
(run NULL) podem coexistir legitimamente. ``CREATE UNIQUE INDEX ... WHERE``
funciona em SQLite e Postgres (precedente: ``ux_documents_workspace_content_hash``,
migration f1a2b3c4d5e6) — sem ``batch_alter_table``, sem ADD CONSTRAINT.

Detecta duplicatas pré-existentes ANTES de criar o índice e aborta com
mensagem clara (não apaga Reports — dado do usuário; resolução é manual).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import context, op

revision: str = "rel03reportuniq"
down_revision: Union[str, Sequence[str], None] = "adr291baserun"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_INDEX_NAME = "ux_reports_workspace_pipeline_run"


def _preexisting_duplicates(bind) -> list:
    return bind.execute(
        sa.text(
            "SELECT workspace_id, pipeline_run_id, COUNT(*) AS c "
            "FROM reports WHERE pipeline_run_id IS NOT NULL "
            "GROUP BY workspace_id, pipeline_run_id HAVING COUNT(*) > 1"
        )
    ).fetchall()


def upgrade() -> None:
    # Offline (--sql): sem conexão para consultar duplicatas; emite só o DDL.
    # A detecção roda na migração online sobre o DB-alvo.
    dups = [] if context.is_offline_mode() else _preexisting_duplicates(op.get_bind())
    if dups:
        offenders = [(r[0], r[1], r[2]) for r in dups[:10]]
        raise RuntimeError(
            f"REL-03: não posso criar índice único — {len(dups)} grupo(s) "
            f"(workspace_id, pipeline_run_id) duplicado(s) em reports. "
            f"Resolva manualmente antes de migrar (amostra: {offenders})."
        )
    op.execute(
        f"""
        CREATE UNIQUE INDEX IF NOT EXISTS {_INDEX_NAME}
        ON reports (workspace_id, pipeline_run_id)
        WHERE pipeline_run_id IS NOT NULL
        """
    )


def downgrade() -> None:
    op.execute(f"DROP INDEX IF EXISTS {_INDEX_NAME}")
