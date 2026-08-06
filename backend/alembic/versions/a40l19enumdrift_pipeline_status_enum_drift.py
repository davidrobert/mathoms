"""A40.l19 (ADR-357 §7): drift dos enums de status do pipeline.

Revision ID: a40l19enumdrift
Revises: adr362execrev
Create Date: 2026-08-06

A migration inicial (``0412b148b9d6``) criou ``pipelinestagestatus`` com 5
valores e ``pipelinerunstatus`` com 6. O Python declara 8 em cada hoje, e
nenhum ``ALTER TYPE`` foi escrito para os que entraram depois:

    pipelinestagestatus  falta: skipped_free_tier, needs_review, degraded
    pipelinerunstatus    falta: needs_review, resuming

Funciona porque dev/CI roda SQLite, onde a coluna é VARCHAR sem CHECK
(SQLAlchemy 2.x usa ``create_constraint=False``). Em Postgres o ``INSERT``
explode — e dois desses caminhos já estão VIVOS: ``skipped_free_tier`` é
escrito em todo run de tier free com stage LLM, e ``needs_review`` do stage
log vem de E3 determinístico (ADR-272). Não é quebra futura; é quebra armada
esperando o cutover.

``degraded`` (ADR-357 §3) ainda não tem writer — o da A40.l18 vem depois.
Entra aqui porque o invariante é ``python ⊆ tipo do DB``, direção única:
alargar o store primeiro e armar o writer depois.

Downgrade: Postgres não suporta ``DROP VALUE``. Mesma política das migrations
``adr238informes2``/``adr239vehicles2`` — pre-down guard contra rows usando os
valores novos, depois no-op informativo.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "a40l19enumdrift"
down_revision: Union[str, Sequence[str], None] = "adr362execrev"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_GUARDED_ROWS: tuple[tuple[str, str, str], ...] = (
    ("pipeline_stage_logs", "status", "skipped_free_tier"),
    ("pipeline_stage_logs", "status", "needs_review"),
    ("pipeline_stage_logs", "status", "degraded"),
    ("pipeline_runs", "status", "needs_review"),
    ("pipeline_runs", "status", "resuming"),
)


def upgrade() -> None:
    """ALTER TYPE ... ADD VALUE em Postgres; no-op em SQLite."""
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    # Statements literais, não loop sobre tupla: é a forma que
    # `dev/check_enum_migration_parity.py` lê por AST, e a que os precedentes
    # (adr238informes2, adr239vehicles2) já usam. Um f-string aqui tornaria
    # esta migration invisível ao gate.
    # PG 12+ aceita ADD VALUE em transação desde que o label não seja USADO na
    # mesma transação — esta migration só declara.
    op.execute("ALTER TYPE pipelinestagestatus ADD VALUE IF NOT EXISTS 'skipped_free_tier'")
    op.execute("ALTER TYPE pipelinestagestatus ADD VALUE IF NOT EXISTS 'needs_review'")
    op.execute("ALTER TYPE pipelinestagestatus ADD VALUE IF NOT EXISTS 'degraded'")
    op.execute("ALTER TYPE pipelinerunstatus ADD VALUE IF NOT EXISTS 'needs_review'")
    op.execute("ALTER TYPE pipelinerunstatus ADD VALUE IF NOT EXISTS 'resuming'")


def downgrade() -> None:
    """Pre-down guard; Postgres não suporta DROP VALUE em enum existente."""
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    import sqlalchemy as sa

    for table, column, value in _GUARDED_ROWS:
        n = bind.execute(
            sa.text(f"SELECT COUNT(*) FROM {table} WHERE {column} = :v"), {"v": value}
        ).scalar()
        if n and int(n) > 0:
            raise RuntimeError(
                f"A40.l19 downgrade bloqueado: {n} row(s) em {table}.{column} "
                f"com '{value}'. UPDATE para um valor da migration inicial antes "
                f"do downgrade. Postgres não permite DROP VALUE; este downgrade "
                f"é informativo apenas."
            )
    op.execute(
        "-- A40.l19 downgrade: Postgres não suporta DROP VALUE. Os 5 valores "
        "permanecem nos enums (no-op)."
    )
