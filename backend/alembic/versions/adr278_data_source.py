"""ADR-278 (revision adr278datasource, revises adr282overridenk) — eixo central da Onda 1
do Data Lineage: cria ``data_source`` (fonte plugável) + coluna nullable indexada
``pipeline_artifacts.data_source_id`` (``document_id`` permanece). FK ``ON DELETE SET NULL``
é DDL Postgres-específico → lane ``dl-f1-migration-runbook``. Backfill idempotente: 1
``data_source`` ``kind='document'`` por workspace com E2+``document_id``. Sentinela ``''`` em
``institution_code``/``external_account_ref`` (NULL quebraria o unique no Postgres). Índice
simples (CONCURRENTLY em escala fica no runbook G-e, precedente ADR-275/282)."""

import uuid
from datetime import datetime, timezone
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "adr278datasource"
down_revision: Union[str, Sequence[str], None] = "adr282overridenk"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_DS_INDEX = "ix_data_source_workspace_id"
_PA_INDEX = "ix_pipeline_artifacts_data_source_id"


def _ds_table() -> sa.Table:
    return sa.table(
        "data_source",
        sa.column("id"),
        sa.column("workspace_id"),
        sa.column("kind"),
        sa.column("institution_code"),
        sa.column("external_account_ref"),
        sa.column("display_name"),
        sa.column("created_at"),
    )


def _pa_table() -> sa.Table:
    return sa.table(
        "pipeline_artifacts",
        sa.column("workspace_id"),
        sa.column("document_id"),
        sa.column("data_source_id"),
    )


def _ensure_document_source(bind, ds: sa.Table, workspace_id: str, now: datetime) -> str:
    """Acha (idempotente) ou cria o ``data_source`` ``kind='document'`` do workspace."""
    existing = bind.execute(
        sa.select(ds.c.id).where(
            ds.c.workspace_id == workspace_id,
            ds.c.kind == "document",
            ds.c.institution_code == "",
            ds.c.external_account_ref == "",
        )
    ).first()
    if existing:
        return existing[0]
    ds_id = str(uuid.uuid4())
    bind.execute(
        ds.insert().values(
            id=ds_id,
            workspace_id=workspace_id,
            kind="document",
            institution_code="",
            external_account_ref="",
            display_name="Documentos",
            created_at=now,
        )
    )
    return ds_id


def _backfill_document_sources() -> None:
    bind = op.get_bind()
    ds, pa = _ds_table(), _pa_table()
    now = datetime.now(timezone.utc)
    workspaces = bind.execute(
        sa.select(pa.c.workspace_id).where(pa.c.document_id.isnot(None)).distinct()
    ).fetchall()
    for (workspace_id,) in workspaces:
        ds_id = _ensure_document_source(bind, ds, workspace_id, now)
        bind.execute(
            pa.update()
            .where(pa.c.workspace_id == workspace_id, pa.c.document_id.isnot(None))
            .values(data_source_id=ds_id)
        )


def upgrade() -> None:
    op.create_table(
        "data_source",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.String(length=36),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("institution_code", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("external_account_ref", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "workspace_id",
            "kind",
            "institution_code",
            "external_account_ref",
            name="uq_data_source_natural_key",
        ),
    )
    op.create_index(_DS_INDEX, "data_source", ["workspace_id"])
    # Coluna sem FK DB aqui (portável SQLite/Alembic). O FK ON DELETE SET NULL
    # (ADR-278) é DDL Postgres-específico (NOT VALID + VALIDATE em tabela de alto
    # volume) e entra na lane dl-f1-migration-runbook. Integridade via app layer.
    op.add_column(
        "pipeline_artifacts", sa.Column("data_source_id", sa.String(length=36), nullable=True)
    )
    op.create_index(_PA_INDEX, "pipeline_artifacts", ["data_source_id"])
    # Backfill lê dados (SELECT por workspace) → impossível em modo offline `--sql`.
    if not op.get_context().as_sql:
        _backfill_document_sources()


def downgrade() -> None:
    op.drop_index(_PA_INDEX, table_name="pipeline_artifacts")
    op.drop_column("pipeline_artifacts", "data_source_id")
    op.drop_index(_DS_INDEX, table_name="data_source")
    op.drop_table("data_source")
