"""Close orphan Goal rows whose `type` is not in `VALID_GOAL_TYPES` (ADR-180 follow-up).

Sprint A10.6 (ADR-180) removeu ``PLANNING_CONTEXT`` de
``VALID_GOAL_TYPES`` em ``backend/app/models/goal.py``, mas não fez
backfill de dados. Workspaces seedados antes do cutover ainda têm rows
com ``type='PLANNING_CONTEXT'`` (e potencialmente outros tipos legados)
com ``effective_to IS NULL`` — vigentes do ponto de vista da query e
vazando para o card "Metas vigentes neste ciclo" do relatório como label
cru em UPPER_SNAKE.

Mitigação prévia: commit ``0053d15`` adicionou filtro defensivo no
snapshot builder e no frontend. Esta migration é o cleanup definitivo no
DB.

Comportamento:
- Para cada row em ``goals`` com ``effective_to IS NULL`` e
  ``type`` fora do contrato A10.6, seta
  ``effective_to = CURRENT_DATE - 1 day`` (mesmo padrão de
  ``_close_existing`` em ``seed_goals_workspace.py``).
- Idempotente: re-runs após o primeiro apply são no-op (rows já fechadas
  não voltam ao filtro ``effective_to IS NULL``).
- Skip silencioso em offline mode (``alembic upgrade head --sql``) — UPDATE
  com data dinâmica exige round-trip ao DB.

Os tipos válidos estão hardcoded como snapshot da decisão A10.6 (ADR-180)
intencionalmente: migrations precisam ser determinísticas mesmo se
``VALID_GOAL_TYPES`` evoluir no futuro. Se um novo cleanup for necessário
após adicionar novo tipo, escreva nova migration.

Revision ID: d2c3d4e5f6a7
Revises: c9d0e1f2a3b4
Create Date: 2026-05-12
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import context, op

revision: str = "d2c3d4e5f6a7"
down_revision: Union[str, Sequence[str], None] = "e1f2a3b4c5d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

logger = logging.getLogger("alembic.runtime.migration")

# Snapshot do contrato A10.6 (ADR-180). NÃO importar de
# ``backend.app.models.goal`` — migrations devem ser determinísticas
# mesmo que ``VALID_GOAL_TYPES`` evolua em sprints futuras.
_VALID_GOAL_TYPES_A10_6: tuple[str, ...] = (
    "INDEPENDENCIA_FINANCEIRA",
    "APORTE_MENSAL",
    "DOLARIZACAO",
    "ALOCACAO_ALVO",
)


def upgrade() -> None:
    if context.is_offline_mode():
        return

    bind = op.get_bind()
    yesterday = date.today() - timedelta(days=1)

    orphans = bind.execute(
        sa.text(
            "SELECT type, COUNT(*) AS n FROM goals "
            "WHERE effective_to IS NULL AND type NOT IN :valid_types "
            "GROUP BY type"
        ).bindparams(sa.bindparam("valid_types", expanding=True)),
        {"valid_types": list(_VALID_GOAL_TYPES_A10_6)},
    ).fetchall()

    if not orphans:
        logger.info("close_orphan_goal_types: 0 rows to close")
        return

    for row in orphans:
        logger.info("close_orphan_goal_types: closing type=%s count=%d", row.type, row.n)

    result = bind.execute(
        sa.text(
            "UPDATE goals SET effective_to = :yesterday "
            "WHERE effective_to IS NULL AND type NOT IN :valid_types"
        ).bindparams(sa.bindparam("valid_types", expanding=True)),
        {"yesterday": yesterday, "valid_types": list(_VALID_GOAL_TYPES_A10_6)},
    )
    logger.info("close_orphan_goal_types: rowcount=%d", result.rowcount)


def downgrade() -> None:
    # Não há downgrade seguro: reverter exigiria saber quais rows foram
    # fechadas por esta migration vs. fechadas legitimamente antes —
    # informação não preservada.
    pass
