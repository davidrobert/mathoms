"""ADR-291: pipeline_runs.base_run_id — lineage do run base em from_stage.

Revision ID: adr291baserun
Revises: adr290supersede
Create Date: 2026-06-12

Run disparado com ``from_stage`` lê os stages run-scoped upstream
(E3/E4/E5) de um run base coerente via fallback pinado no
``DBArtifactStore``. A coluna registra QUAL run foi escolhido pelo
resolver do trigger — lineage consultável (complemento de
``pipeline_artifacts.data_source_id``, ADR-278).

NULL = run full/incremental/resume (sem base). FK self-referencial
``ON DELETE SET NULL`` é Postgres-only via ``ADD CONSTRAINT`` (padrão
adr278datasourcefk — SQLite não suporta ADD CONSTRAINT e batch mode
quebra ``upgrade --sql``; integridade via app layer em testes). Coluna
nasce 100% NULL → ``NOT VALID`` + ``VALIDATE`` são instantâneos, mas
mantêm a higiene de lock do precedente.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "adr291baserun"
down_revision: Union[str, Sequence[str], None] = "adr290supersede"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_FK_NAME = "fk_pipeline_runs_base_run_id"


def _is_postgres() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def upgrade() -> None:
    op.add_column("pipeline_runs", sa.Column("base_run_id", sa.String(length=36), nullable=True))
    if not _is_postgres():
        return
    with op.get_context().autocommit_block():
        op.execute(
            f"ALTER TABLE pipeline_runs ADD CONSTRAINT {_FK_NAME} "
            "FOREIGN KEY (base_run_id) REFERENCES pipeline_runs (id) "
            "ON DELETE SET NULL NOT VALID"
        )
        op.execute(f"ALTER TABLE pipeline_runs VALIDATE CONSTRAINT {_FK_NAME}")


def downgrade() -> None:
    if _is_postgres():
        op.execute(f"ALTER TABLE pipeline_runs DROP CONSTRAINT IF EXISTS {_FK_NAME}")
    op.drop_column("pipeline_runs", "base_run_id")
