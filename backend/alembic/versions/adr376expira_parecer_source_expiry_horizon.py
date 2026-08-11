"""adr-376 expiração por parecer-fonte — horizon, run lineage, unique parcial

Revision ID: adr376expira
Revises: a40l20parecerout
Create Date: 2026-08-11

ADR-376: (§D4) coluna ``horizon`` nullable (bucket temporal do parecer,
descartado até aqui na persistência); (§D1) ``pipeline_run_id`` nullable
com FK SET NULL — torna explícito o predicado "não foi criada pelo run
atual" da expiração; FK SET NULL também em ``superseded_by_run_id``
(soft reference que escapava do gate de coverage por nome); (§D3)
substituição do UNIQUE full ``uq_sugagg_ws_dedup_status`` pelo índice
único parcial ``uq_sugagg_ws_dedup_ativa`` (ws, dedup_key) WHERE status
ativo. Motivo: com "último parecer vence" a mesma dedup_key pode ser
Superseded N vezes — o full unique quebrava na 2ª (e já quebrava no 2º
descarte da mesma key no caminho determinístico). Sem backfill (a
expiração ADR-376 limpa o legado no run entregue seguinte). Duplicatas
ativas pré-existentes: medidas em 2026-08-11 no dogfood = zero.

Downgrade: destrutivo-documentado — antes de recriar o UNIQUE full,
remove duplicatas (ws, dedup_key, status) mantendo a row mais recente
(rowid máximo), senão a recriação falharia sobre dados pós-upgrade.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "adr376expira"
down_revision: Union[str, None] = "a40l20parecerout"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_PARTIAL_UNIQUE = "uq_sugagg_ws_dedup_ativa"
_LEGACY_UNIQUE = "uq_sugagg_ws_dedup_status"
_ACTIVE_WHERE = "status IN ('Pendente', 'Aceita', 'Modificada')"


def upgrade() -> None:
    with op.batch_alter_table("suggestions", schema=None) as batch_op:
        batch_op.add_column(sa.Column("horizon", sa.String(length=16), nullable=True))
        batch_op.add_column(sa.Column("pipeline_run_id", sa.String(length=36), nullable=True))
        batch_op.create_foreign_key(
            "fk_sugagg_pipeline_run_id",
            "pipeline_runs",
            ["pipeline_run_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_foreign_key(
            "fk_sugagg_superseded_by_run_id",
            "pipeline_runs",
            ["superseded_by_run_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.drop_constraint(_LEGACY_UNIQUE, type_="unique")
    op.create_index(
        _PARTIAL_UNIQUE,
        "suggestions",
        ["workspace_id", "dedup_key"],
        unique=True,
        sqlite_where=sa.text(_ACTIVE_WHERE),
        postgresql_where=sa.text(_ACTIVE_WHERE),
    )


def downgrade() -> None:
    op.drop_index(_PARTIAL_UNIQUE, table_name="suggestions")
    op.execute(
        sa.text(
            "DELETE FROM suggestions WHERE rowid NOT IN ("
            "SELECT MAX(rowid) FROM suggestions "
            "GROUP BY workspace_id, dedup_key, status)"
        )
    )
    with op.batch_alter_table("suggestions", schema=None) as batch_op:
        batch_op.drop_constraint("fk_sugagg_superseded_by_run_id", type_="foreignkey")
        batch_op.drop_constraint("fk_sugagg_pipeline_run_id", type_="foreignkey")
        batch_op.drop_column("pipeline_run_id")
        batch_op.drop_column("horizon")
        batch_op.create_unique_constraint(_LEGACY_UNIQUE, ["workspace_id", "dedup_key", "status"])
