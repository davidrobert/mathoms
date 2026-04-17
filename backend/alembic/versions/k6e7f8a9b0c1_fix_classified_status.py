"""documents: corrige status 'classified' inválido → 'ready'

O valor 'classified' nunca fez parte do enum DocumentStatus (que usa
'classifying' como estado transitório e 'ready' como estado final de
classificação bem-sucedida). Documentos com esse status foram criados
por código legado antes da formalização da state machine (P1.1).

Como 'classified' semanticamente equivale a 'ready' (classificação
concluída com sucesso), a migração atualiza esses registros para o
valor canônico correto. Sem essa correção o SQLAlchemy lança ValueError
ao desserializar as linhas, derrubando o endpoint GET /documents inteiro.

Revision ID: k6e7f8a9b0c1
Revises: j5d6e7f8a9b0
Create Date: 2026-04-17
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "k6e7f8a9b0c1"
down_revision: Union[str, None] = "j5d6e7f8a9b0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE documents SET status = 'ready' WHERE status = 'classified'"
        )
    )


def downgrade() -> None:
    # Não é possível identificar com segurança quais rows eram 'classified'
    # após o upgrade; o downgrade é intencional noop.
    pass
