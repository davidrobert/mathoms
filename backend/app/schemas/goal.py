"""Legacy shim para ``schemas.goal``.

Os DTOs canônicos do agregado ``Goal`` vivem em
``backend/app/schemas/dto/goal/`` (A6e.6 — ADR-101). Este módulo
re-exporta com os nomes antigos para que:

- callers legados (seed scripts, factory builders, testes)
  continuem passando sem modificação;
- integrações externas que possam ter importado esses símbolos não
  quebrem durante a janela de migração.

``*UpsertRequest`` vira alias de ``*UpsertCommand`` — nomenclatura A6e
é "command" (uma intenção), não "request" (o transporte HTTP).

Preferir nas chamadas novas::

    from backend.app.schemas.dto.goal import (
        IFGoalInputs, IFGoalDerived, IFGoalResponse, IFGoalUpsertCommand, ...
    )
"""

from __future__ import annotations

from backend.app.schemas.dto.goal.alocacao import (
    AlocacaoGoalComputeRequest,
    AlocacaoGoalComputeResponse,
    AlocacaoGoalDerived,
    AlocacaoGoalHistoryResponse,
    AlocacaoGoalInputs,
    AlocacaoGoalResponse,
)
from backend.app.schemas.dto.goal.alocacao import (
    AlocacaoGoalUpsertCommand as AlocacaoGoalUpsertRequest,
)
from backend.app.schemas.dto.goal.aporte import (
    AporteGoalComputeRequest,
    AporteGoalComputeResponse,
    AporteGoalDerived,
    AporteGoalHistoryResponse,
    AporteGoalInputs,
    AporteGoalResponse,
)
from backend.app.schemas.dto.goal.aporte import (
    AporteGoalUpsertCommand as AporteGoalUpsertRequest,
)
from backend.app.schemas.dto.goal.base import GoalResponseBase as _GoalResponseBase
from backend.app.schemas.dto.goal.dolar import (
    DolarGoalComputeRequest,
    DolarGoalComputeResponse,
    DolarGoalDerived,
    DolarGoalHistoryResponse,
    DolarGoalInputs,
    DolarGoalResponse,
)
from backend.app.schemas.dto.goal.dolar import (
    DolarGoalUpsertCommand as DolarGoalUpsertRequest,
)
from backend.app.schemas.dto.goal.if_goal import (
    IFGoalComputeRequest,
    IFGoalComputeResponse,
    IFGoalDerived,
    IFGoalHistoryResponse,
    IFGoalInputs,
    IFGoalResponse,
)
from backend.app.schemas.dto.goal.if_goal import (
    IFGoalUpsertCommand as IFGoalUpsertRequest,
)

__all__ = [
    "AlocacaoGoalComputeRequest",
    "AlocacaoGoalComputeResponse",
    "AlocacaoGoalDerived",
    "AlocacaoGoalHistoryResponse",
    "AlocacaoGoalInputs",
    "AlocacaoGoalResponse",
    "AlocacaoGoalUpsertRequest",
    "AporteGoalComputeRequest",
    "AporteGoalComputeResponse",
    "AporteGoalDerived",
    "AporteGoalHistoryResponse",
    "AporteGoalInputs",
    "AporteGoalResponse",
    "AporteGoalUpsertRequest",
    "DolarGoalComputeRequest",
    "DolarGoalComputeResponse",
    "DolarGoalDerived",
    "DolarGoalHistoryResponse",
    "DolarGoalInputs",
    "DolarGoalResponse",
    "DolarGoalUpsertRequest",
    "IFGoalComputeRequest",
    "IFGoalComputeResponse",
    "IFGoalDerived",
    "IFGoalHistoryResponse",
    "IFGoalInputs",
    "IFGoalResponse",
    "IFGoalUpsertRequest",
    "_GoalResponseBase",
]
