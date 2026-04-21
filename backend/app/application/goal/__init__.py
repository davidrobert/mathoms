"""Use cases do agregado ``Goal`` (ADR-101 R15 · ADR-073).

Os 4 tipos de meta (``INDEPENDENCIA_FINANCEIRA``, ``APORTE_MENSAL``,
``DOLARIZACAO``, ``ALOCACAO_ALVO``) versionados append-only. Cada
endpoint de ``/workspaces/{id}/goals/...`` delega a um use case aqui.

Compute functions (``compute_if_derived`` etc.) permanecem em
``backend.app.services.goal_service`` — são **domínio puro** e use cases
chamam-nas diretamente.
"""

from backend.app.application.goal.compute_alocacao_projection import (
    compute_alocacao_projection,
)
from backend.app.application.goal.compute_aporte_projection import (
    compute_aporte_projection,
)
from backend.app.application.goal.compute_dolar_projection import (
    compute_dolar_projection,
)
from backend.app.application.goal.compute_if_projection import (
    compute_if_projection,
)
from backend.app.application.goal.create_if_goal_version import (
    create_if_goal_version,
)
from backend.app.application.goal.create_typed_goal_version import (
    create_typed_goal_version,
)
from backend.app.application.goal.get_active_if_goal import get_active_if_goal
from backend.app.application.goal.get_active_typed_goal import (
    get_active_typed_goal,
)
from backend.app.application.goal.list_if_goal_versions import (
    list_if_goal_versions,
)
from backend.app.application.goal.list_typed_goal_versions import (
    list_typed_goal_versions,
)

__all__ = [
    "compute_alocacao_projection",
    "compute_aporte_projection",
    "compute_dolar_projection",
    "compute_if_projection",
    "create_if_goal_version",
    "create_typed_goal_version",
    "get_active_if_goal",
    "get_active_typed_goal",
    "list_if_goal_versions",
    "list_typed_goal_versions",
]
