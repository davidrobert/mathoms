"""phase5_celery_task_id

Revision ID: b5c6d7e8f9a0
Revises: a1b2c3d4e5f6
Create Date: 2026-04-14 20:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b5c6d7e8f9a0'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('pipeline_runs') as batch_op:
        batch_op.add_column(sa.Column('celery_task_id', sa.String(length=255), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('pipeline_runs') as batch_op:
        batch_op.drop_column('celery_task_id')
