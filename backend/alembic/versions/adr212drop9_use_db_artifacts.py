"""ADR-212 PR4 — drop workspaces.use_db_artifacts_override (sunset DiskArtifactStore).

Revision ID: adr212drop9
Revises: f4e5d6c7b8a9
Create Date: 2026-05-14

ADR-212 §PR4: completa o sunset de ``MATHOMS_USE_DB_ARTIFACTS`` + ``DiskArtifactStore``.

A coluna ``workspaces.use_db_artifacts_override`` foi introduzida em
ADR-106 (migration ``r6s7t8u9v0w1``) como opt-in por-workspace para o
``DBArtifactStore``. PR3a (commit ``688c13d``) hard-wired ``DBArtifactStore``
no Celery worker — a coluna deixou de ser consultada em runtime. PR3b
deletou ``DiskArtifactStore`` class. Este PR4 fecha o ciclo dropando a
coluna do schema + removendo ``USE_DB_ARTIFACTS`` de ``settings``.

**Guard pré-drop** (data-engineer P0): aborta migration se algum
workspace ainda tem ``use_db_artifacts_override`` setado (qualquer
valor não-NULL). Em produção esperamos count=0 (override nunca foi
usado em prod desde ADR-118).

**Reversibilidade:** ``downgrade()`` recria coluna ``nullable=True`` —
estrutura reversível, **dados perdidos** (overrides hipotéticos não
podem ser restaurados sem snapshot DB pré-PR4).

**Portabilidade SQLite ↔ Postgres:** usa ``op.batch_alter_table`` porque
SQLite emula ``DROP COLUMN`` via rebuild + copy + swap.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import MetaData, Table, text

# revision identifiers, used by Alembic.
revision: str = "adr212drop9"
down_revision: str | None = "f4e5d6c7b8a9"
branch_labels = None
depends_on = None


def _workspaces_table_definition() -> Table:
    """Definição completa de ``workspaces`` para ``batch_alter_table(copy_from=...)``.

    SQLite em offline mode (``alembic upgrade --sql``) não consegue refletir
    o schema; precisamos passar a tabela explicitamente. Schema espelha
    ``backend/app/models/workspace.py`` no estado **anterior** ao drop
    (com a coluna ``use_db_artifacts_override`` ainda presente).
    """
    return Table(
        "workspaces",
        MetaData(),
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("family_surname", sa.String(255), nullable=True),
        sa.Column(
            "owner_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("use_db_artifacts_override", sa.Boolean(), nullable=True),
        sa.Column(
            "monthly_llm_budget_usd",
            sa.Numeric(10, 2),
            nullable=False,
            server_default="5.00",
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("business_profile_json", sa.JSON(), nullable=True),
        sa.Column("rule_cap_override", sa.Integer(), nullable=True),
    )


def upgrade() -> None:
    # Guard: aborta se algum workspace ainda tem override setado em prod.
    # PR3a+PR3b hard-wired DBArtifactStore — a coluna não tem leitores.
    # Em offline mode (`alembic upgrade --sql`) bind não suporta execute;
    # skipamos guard (operador deve validar count manualmente antes do deploy).
    if not op.get_context().as_sql:
        result = (
            op.get_bind()
            .execute(
                text("SELECT count(*) FROM workspaces WHERE use_db_artifacts_override IS NOT NULL")
            )
            .scalar()
        )
        if result and result > 0:
            raise RuntimeError(
                f"{result} workspace(s) com use_db_artifacts_override setado — "
                "investigar antes de drop (ADR-212 PR4 §Guard pré-drop)."
            )

    with op.batch_alter_table("workspaces", copy_from=_workspaces_table_definition()) as batch:
        batch.drop_column("use_db_artifacts_override")


def downgrade() -> None:
    """Recria coluna; estrutura reversível, dados perdidos (overrides não
    podem ser restaurados sem snapshot DB pré-upgrade).
    """
    # Para downgrade precisamos da definição pós-drop (sem a coluna).
    post_drop_def = Table(
        "workspaces",
        MetaData(),
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("family_surname", sa.String(255), nullable=True),
        sa.Column(
            "owner_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "monthly_llm_budget_usd",
            sa.Numeric(10, 2),
            nullable=False,
            server_default="5.00",
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("business_profile_json", sa.JSON(), nullable=True),
        sa.Column("rule_cap_override", sa.Integer(), nullable=True),
    )
    with op.batch_alter_table("workspaces", copy_from=post_drop_def) as batch:
        batch.add_column(sa.Column("use_db_artifacts_override", sa.Boolean(), nullable=True))
