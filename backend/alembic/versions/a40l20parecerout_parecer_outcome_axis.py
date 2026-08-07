"""A40.l20 (ADR-366): desfecho da geração do parecer como eixo próprio.

Revision ID: a40l20parecerout
Revises: a40l19enumdrift
Create Date: 2026-08-06

Três colunas em ``planner_review_metadata``:

    outcome              desfecho da geração (ADR-366 §D1)
    retention_reason     motivo client-facing, NULL fora dos desfechos retidos (§D3)
    items_dropped_count  itens retidos por qualidade, ≠ items_gated_count (§D4)

``status`` **não** é tocado: continua sendo o eixo de publicação da ADR-204 §D1,
com os mesmos 4 valores e as mesmas transições. Nenhum ``ALTER TYPE`` aqui —
``status`` é ``VARCHAR(20)`` sem CHECK nos dois dialetos, e as colunas novas são
``VARCHAR``/``INTEGER``, não enum SQL. É deliberado: mantém fora do caminho a
classe de drift que a ADR-357 §7 documenta.

Backfill: ``outcome`` nasce ``nao_registrado`` nas rows existentes. Afirmar
``entregue`` sobre elas seria afirmar completude sobre runs que sabidamente
perderam itens — o dano que a A40.l22 chama de dúvida retroativa. Membro
explícito e não NULL, pelo mesmo motivo que ``cost_known`` existe (A40.l17):
"zero real" e "desconhecido" têm de ser distinguíveis no tipo.

Não há backfill possível para rows de parecer retido histórico: o artifact do
desfecho retido é rolled-back hoje, e ``pipeline_artifact_id`` é NOT NULL +
UNIQUE — não há onde apontar. Backfill que exigiria fabricar a evidência que
deveria preservar não se faz. A telemetria histórica sobrevive em
``pipeline_stage_logs.output_summary``.

Downgrade: ``drop_column`` × 3, reversível de verdade.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a40l20parecerout"
down_revision: Union[str, Sequence[str], None] = "a40l19enumdrift"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLE = "planner_review_metadata"


def upgrade() -> None:
    """Adiciona as 3 colunas com server_default (PG 11+ não reescreve a tabela)."""
    with op.batch_alter_table(_TABLE) as batch:
        batch.add_column(
            sa.Column(
                "outcome",
                sa.String(length=32),
                nullable=False,
                server_default="nao_registrado",
            )
        )
        batch.add_column(sa.Column("retention_reason", sa.String(length=48), nullable=True))
        batch.add_column(
            sa.Column(
                "items_dropped_count",
                sa.Integer(),
                nullable=False,
                server_default="0",
            )
        )


def downgrade() -> None:
    with op.batch_alter_table(_TABLE) as batch:
        batch.drop_column("items_dropped_count")
        batch.drop_column("retention_reason")
        batch.drop_column("outcome")
