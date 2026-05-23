"""DTOs do agregado ``Goal`` (4 tipos versionados: IF, Aportes, Dólar, Alocação).

Cada tipo tem 4 DTOs: Inputs (user-provided), Derived (computed),
Response (persisted + enriched), UpsertCommand (write input).
Compute request/response vivem em módulos por tipo também.

Re-exports convenientes — prefira estes imports ao invés de alcançar
módulos internos, para manter o pacote como fronteira do agregado.
"""

from backend.app.schemas.dto.goal.alocacao import (
    AlocacaoGoalComputeRequest,
    AlocacaoGoalComputeResponse,
    AlocacaoGoalDerived,
    AlocacaoGoalHistoryResponse,
    AlocacaoGoalInputs,
    AlocacaoGoalResponse,
    AlocacaoGoalUpsertCommand,
)
from backend.app.schemas.dto.goal.aporte import (
    AporteGoalComputeRequest,
    AporteGoalComputeResponse,
    AporteGoalDerived,
    AporteGoalHistoryResponse,
    AporteGoalInputs,
    AporteGoalResponse,
    AporteGoalUpsertCommand,
)
from backend.app.schemas.dto.goal.base import GoalResponseBase
from backend.app.schemas.dto.goal.dolar import (
    DolarGoalComputeRequest,
    DolarGoalComputeResponse,
    DolarGoalDerived,
    DolarGoalHistoryResponse,
    DolarGoalInputs,
    DolarGoalResponse,
    DolarGoalUpsertCommand,
)
from backend.app.schemas.dto.goal.if_goal import (
    IFGoalComputeRequest,
    IFGoalComputeResponse,
    IFGoalDerived,
    IFGoalHistoryResponse,
    IFGoalInputs,
    IFGoalResponse,
    IFGoalUpsertCommand,
)
from backend.app.schemas.dto.goal.mapper import (
    GOAL_TYPE_DTO_CLASSES,
    goal_to_if_response,
    goal_to_typed_response,
    meta_version_from_params,
)
from backend.app.schemas.dto.goal.reserva_emergencia import (
    ReservaEmergenciaGoalComputeRequest,
    ReservaEmergenciaGoalComputeResponse,
    ReservaEmergenciaGoalDerived,
    ReservaEmergenciaGoalHistoryResponse,
    ReservaEmergenciaGoalInputs,
    ReservaEmergenciaGoalResponse,
    ReservaEmergenciaGoalUpsertCommand,
)

__all__ = [
    "AlocacaoGoalComputeRequest",
    "AlocacaoGoalComputeResponse",
    "AlocacaoGoalDerived",
    "AlocacaoGoalHistoryResponse",
    "AlocacaoGoalInputs",
    "AlocacaoGoalResponse",
    "AlocacaoGoalUpsertCommand",
    "AporteGoalComputeRequest",
    "AporteGoalComputeResponse",
    "AporteGoalDerived",
    "AporteGoalHistoryResponse",
    "AporteGoalInputs",
    "AporteGoalResponse",
    "AporteGoalUpsertCommand",
    "DolarGoalComputeRequest",
    "DolarGoalComputeResponse",
    "DolarGoalDerived",
    "DolarGoalHistoryResponse",
    "DolarGoalInputs",
    "DolarGoalResponse",
    "DolarGoalUpsertCommand",
    "GOAL_TYPE_DTO_CLASSES",
    "GoalResponseBase",
    "IFGoalComputeRequest",
    "IFGoalComputeResponse",
    "IFGoalDerived",
    "IFGoalHistoryResponse",
    "IFGoalInputs",
    "IFGoalResponse",
    "IFGoalUpsertCommand",
    "ReservaEmergenciaGoalComputeRequest",
    "ReservaEmergenciaGoalComputeResponse",
    "ReservaEmergenciaGoalDerived",
    "ReservaEmergenciaGoalHistoryResponse",
    "ReservaEmergenciaGoalInputs",
    "ReservaEmergenciaGoalResponse",
    "ReservaEmergenciaGoalUpsertCommand",
    "goal_to_if_response",
    "goal_to_typed_response",
    "meta_version_from_params",
]
