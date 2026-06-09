"""ADR-278 — FK ``pipeline_artifacts.data_source_id`` → ``data_source.id`` ``ON DELETE SET NULL`` (revision adr278datasourcefk, revises adr278datasource). Materializa o FK deferido da A23.l5: Postgres-only via ``NOT VALID`` + ``VALIDATE`` em transações SEPARADAS (``autocommit_block``) — o ``ADD`` instantâneo libera ``ACCESS EXCLUSIVE`` antes do scan do ``VALIDATE`` (que roda sob ``SHARE UPDATE EXCLUSIVE``, sem travar escrita). SQLite/Alembic = no-op (FK não existe lá por design — model mantém ``data_source_id`` plain, integridade via app layer; ``_diff_signature`` é cego a FK, sem drift). Remediação idempotente de órfão antes do ``ADD`` (workspace deletado entre adr278 e este FK pode ter deixado ``data_source_id`` apontando para ``data_source`` removido → ``VALIDATE`` falharia inteiro; semântica final é ``SET NULL``). Runbook G-e: ``docs/reference/runbooks/data_lineage_migrations.md``."""

from typing import Sequence, Union

from alembic import op

revision: str = "adr278datasourcefk"
down_revision: Union[str, Sequence[str], None] = "adr278datasource"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_FK_NAME = "fk_pipeline_artifacts_data_source_id"


def _is_postgres() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def _remediate_orphans() -> None:
    op.execute(
        "UPDATE pipeline_artifacts pa SET data_source_id = NULL "
        "WHERE pa.data_source_id IS NOT NULL "
        "AND NOT EXISTS (SELECT 1 FROM data_source ds WHERE ds.id = pa.data_source_id)"
    )


def upgrade() -> None:
    # SQLite/test: FK não materializado (ADR-278 — model plain, integridade app-layer).
    if not _is_postgres():
        return
    if not op.get_context().as_sql:
        _remediate_orphans()
    # NOT VALID (ACCESS EXCLUSIVE, instantâneo) e VALIDATE (SHARE UPDATE EXCLUSIVE) em
    # transações separadas: senão o ADD segura o lock forte durante o scan do VALIDATE.
    with op.get_context().autocommit_block():
        op.execute(
            f"ALTER TABLE pipeline_artifacts ADD CONSTRAINT {_FK_NAME} "
            "FOREIGN KEY (data_source_id) REFERENCES data_source (id) "
            "ON DELETE SET NULL NOT VALID"
        )
        op.execute(f"ALTER TABLE pipeline_artifacts VALIDATE CONSTRAINT {_FK_NAME}")


def downgrade() -> None:
    if not _is_postgres():
        return
    op.execute(f"ALTER TABLE pipeline_artifacts DROP CONSTRAINT IF EXISTS {_FK_NAME}")
