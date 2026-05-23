"""Mapper ORM → DTO para o agregado ``Goal``.

Responsabilidades:

1. ``goal_to_typed_response``: converte ``Goal`` em qualquer response
   tipado (IF, Aporte, Dólar, Alocação), escolhendo as classes corretas
   a partir de ``goal.type`` via ``GOAL_TYPE_DTO_CLASSES``.
2. ``goal_to_if_response``: atalho especializado para o tipo IF —
   preserva compat com o legado ``_goal_to_response`` que só sabia IF.
3. ``meta_version_from_params``: extrai ``params_json.meta_version``
   com fallback seguro.

O mapper **não** recebe ``AsyncSession`` nem ``created_by_name`` do
banco — o caller resolve nomes de autor antes (ex.: via
``resolve_author_names`` helper em ``goal_service``) e passa como
kwarg, mantendo o mapper puro e testável sem DB.
"""

from __future__ import annotations

from typing import Optional

from backend.app.models.goal import Goal
from backend.app.schemas.dto.goal.alocacao import (
    AlocacaoGoalDerived,
    AlocacaoGoalInputs,
    AlocacaoGoalResponse,
)
from backend.app.schemas.dto.goal.aporte import (
    AporteGoalDerived,
    AporteGoalInputs,
    AporteGoalResponse,
)
from backend.app.schemas.dto.goal.base import GoalResponseBase
from backend.app.schemas.dto.goal.dolar import (
    DolarGoalDerived,
    DolarGoalInputs,
    DolarGoalResponse,
)
from backend.app.schemas.dto.goal.if_goal import (
    IFGoalDerived,
    IFGoalInputs,
    IFGoalResponse,
)
from backend.app.schemas.dto.goal.reserva_emergencia import (
    ReservaEmergenciaGoalDerived,
    ReservaEmergenciaGoalInputs,
    ReservaEmergenciaGoalResponse,
)

# Mapeia ``goal.type`` → (response_cls, inputs_cls, derived_cls).
# Ponto único de extensão: novo tipo → adiciona linha aqui + módulo
# correspondente em ``schemas/dto/goal/``.
GOAL_TYPE_DTO_CLASSES: dict[str, tuple[type, type, type]] = {
    "INDEPENDENCIA_FINANCEIRA": (IFGoalResponse, IFGoalInputs, IFGoalDerived),
    "APORTE_MENSAL": (AporteGoalResponse, AporteGoalInputs, AporteGoalDerived),
    "DOLARIZACAO": (DolarGoalResponse, DolarGoalInputs, DolarGoalDerived),
    "ALOCACAO_ALVO": (AlocacaoGoalResponse, AlocacaoGoalInputs, AlocacaoGoalDerived),
    "RESERVA_EMERGENCIA": (
        ReservaEmergenciaGoalResponse,
        ReservaEmergenciaGoalInputs,
        ReservaEmergenciaGoalDerived,
    ),
}


def meta_version_from_params(params_json: Optional[dict] = None) -> int:
    """Extrai ``meta_version`` do ``params_json`` com fallback para 1.

    Tolera:

    - ``params_json`` ausente (``None``) → 1.
    - chave ``meta_version`` ausente → 1.
    - valor ``None`` ou não-coercível para int → 1.

    O meta_version é um contrato com o schema canônico
    (``config/schemas/goal.*.schema.json``) e só incrementa quando o
    shape dos inputs muda de forma incompatível.
    """
    if not params_json:
        return 1
    v = params_json.get("meta_version", 1)
    try:
        return int(v) if v is not None else 1
    except (TypeError, ValueError):
        return 1


def goal_to_typed_response(
    goal: Goal,
    *,
    created_by_name: Optional[str] = None,
) -> GoalResponseBase:
    """Converte ORM ``Goal`` → response tipada por ``goal.type``.

    Pré-condição: ``goal.type`` tem que estar mapeado em
    ``GOAL_TYPE_DTO_CLASSES``. Caso contrário, ``KeyError`` —
    caller é responsável por filtrar tipos desconhecidos.

    Mapper é puro: não bate no DB, não chama compute. ``created_by_name``
    tem que ser resolvido pelo caller (normalmente em batch lookup
    ``User.id → full_name``).
    """
    response_cls, inputs_cls, derived_cls = GOAL_TYPE_DTO_CLASSES[goal.type]
    return response_cls(
        id=goal.id,
        workspace_id=goal.workspace_id,
        type=goal.type,  # type: ignore[arg-type]
        meta_version=meta_version_from_params(goal.params_json),
        inputs=inputs_cls(**goal.params_json["inputs"]),
        derived=derived_cls(**goal.derived_json),
        effective_from=goal.effective_from,
        effective_to=goal.effective_to,
        is_template=goal.is_template,
        notes=goal.notes,
        created_by=goal.created_by,
        created_by_name=created_by_name,
        created_at=goal.created_at,
        updated_at=goal.updated_at,
    )


def goal_to_if_response(
    goal: Goal,
    *,
    created_by_name: Optional[str] = None,
) -> IFGoalResponse:
    """Atalho especializado para o tipo IF.

    Equivalente a ``goal_to_typed_response(goal)`` quando
    ``goal.type == 'INDEPENDENCIA_FINANCEIRA'``, com retorno mais
    narrow para o caller. Preserva compat com o legado
    ``_goal_to_response`` em ``goal_service.py`` que tinha só esta
    assinatura.
    """
    response = goal_to_typed_response(goal, created_by_name=created_by_name)
    assert isinstance(
        response, IFGoalResponse
    ), f"Expected IFGoalResponse, got {type(response).__name__}"
    return response
