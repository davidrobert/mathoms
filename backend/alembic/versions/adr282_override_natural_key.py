"""ADR-282 M1: identidade v2 de transaction_overrides (aditivo, nullable).

Revision ID: adr282overridenk
Revises: adr275auditidx
Create Date: 2026-06-08

Primeira fatia da ADR-282 (fecha D6 da A23.l3): unificar a identidade do
subsistema de override no ``natural_key`` v2 do pipeline, aposentando o terceiro
hash ``generate_transaction_hash`` (``backend/app/services/transaction_service.py``).

Esta migration é **puramente aditiva** — adiciona colunas nullable + 1 índice
parcial. Nenhum read-path consome ``natural_key_hash`` ainda (gate
``override_natural_key_v2_enabled`` off). ``transaction_hash`` legado permanece
e só sai na M2 destrutiva, pós-backfill + cutover.

Colunas:
- ``natural_key_hash`` (String 16) + ``hash_version`` (SmallInt) — o hash v2.
- snapshot dos inputs (``tx_data``/``tx_banco``/``tx_titular``/``tx_tipo_conta``/
  ``tx_valor_cents``/``tx_moeda``/``tx_direction``/``tx_descricao``) — invariante
  ADR-282: a linha é re-hasheável sozinha, sem replay de E4.
- ``orphaned_at`` — quarentena de override que o backfill não reancora (nunca drop).

Índice parcial ``ix_txov_ws_natural_key`` em ``(workspace_id, natural_key_hash)``
WHERE ``natural_key_hash IS NOT NULL AND deleted_at IS NULL`` — caminho de match v2
no cutover (slice 4). Pré-produção: tabela pequena, ``CREATE INDEX`` instantâneo;
em escala, recriar com ``CONCURRENTLY`` (consequência rastreada na ADR-282).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "adr282overridenk"
down_revision: Union[str, Sequence[str], None] = "adr275auditidx"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_NEW_COLUMNS = (
    ("natural_key_hash", sa.String(length=16)),
    ("hash_version", sa.SmallInteger()),
    ("tx_data", sa.String(length=10)),
    ("tx_banco", sa.String(length=255)),
    ("tx_titular", sa.String(length=255)),
    ("tx_tipo_conta", sa.String(length=255)),
    ("tx_valor_cents", sa.Integer()),
    ("tx_moeda", sa.String(length=3)),
    ("tx_direction", sa.String(length=6)),
    ("tx_descricao", sa.Text()),
    ("orphaned_at", sa.DateTime(timezone=True)),
)

_INDEX_NAME = "ix_txov_ws_natural_key"


def upgrade() -> None:
    for name, type_ in _NEW_COLUMNS:
        op.add_column("transaction_overrides", sa.Column(name, type_, nullable=True))
    op.create_index(
        _INDEX_NAME,
        "transaction_overrides",
        ["workspace_id", "natural_key_hash"],
        unique=False,
        sqlite_where=sa.text("natural_key_hash IS NOT NULL AND deleted_at IS NULL"),
        postgresql_where=sa.text("natural_key_hash IS NOT NULL AND deleted_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index(_INDEX_NAME, table_name="transaction_overrides")
    for name, _type in reversed(_NEW_COLUMNS):
        op.drop_column("transaction_overrides", name)
