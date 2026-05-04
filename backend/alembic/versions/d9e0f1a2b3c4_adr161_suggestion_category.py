"""ADR-161 — adiciona ``category`` em suggestions (agrupamento semântico).

Revision ID: d9e0f1a2b3c4
Revises: c8d9e0f1a2b3
Create Date: 2026-05-04

Adiciona coluna ``category`` (String(32), nullable) na tabela
``suggestions`` para agrupar kinds por causa-raiz (ex.: TRS desalinhada
e aporte_abaixo_meta são ambos ``alvo_if``). Permite UI agrupar/filtrar
por category e habilita futura dedup cross-kind.

Mudança apenas aditiva (nullable). Registros pré-existentes ficam com
``NULL`` — backend/frontend trata ausência como "não categorizado".

Nenhum índice — cardinalidade baixa (6 categorias) e queries não
filtram por category isolado; usado como agrupamento em sumário.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d9e0f1a2b3c4"
down_revision: Union[str, Sequence[str], None] = "c8d9e0f1a2b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("suggestions") as batch:
        batch.add_column(sa.Column("category", sa.String(32), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("suggestions") as batch:
        batch.drop_column("category")
