"""add_family_surname_to_workspace

Revision ID: d3f4e5a6b7c8
Revises: 2eb4d38ca788
Create Date: 2026-04-15 17:00:00.000000

Adiciona Workspace.family_surname para preservar `familia.sobrenome`
no `family_members.json` materializado para o pipeline (consumido por E6
em `{{COVER_FAMILIA}}` e no nome do arquivo do relatório).

Antes desta migration o serializer do config_materializer perdia o campo
`familia.sobrenome` ao sobrescrever o arquivo do tenant — relatórios
saíam com a capa em branco para qualquer workspace com membros no DB.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd3f4e5a6b7c8'
down_revision: Union[str, None] = '2eb4d38ca788'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('workspaces', schema=None) as batch_op:
        batch_op.add_column(sa.Column('family_surname', sa.String(length=255), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('workspaces', schema=None) as batch_op:
        batch_op.drop_column('family_surname')
