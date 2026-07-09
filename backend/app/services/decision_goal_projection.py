"""Projeção Decision → Goal (ADR-162).

Quando uma Decision com ``target_field`` populado é marcada
``Executado``, este módulo cria nova versão do Goal correspondente
na **mesma transação** do ``mark_decision_executed``.

Regra invariante: falha de criação de Goal aborta a transição da
Decision (rollback via exceção propagada). Ou ambos persistem, ou
nenhum.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.base.errors import ValidationError
from backend.app.models.decision import Decision
from backend.app.models.goal import Goal
from backend.app.repositories.goal_repository import GoalRepository
from backend.app.schemas.dto.goal import (
    AlocacaoGoalInputsV2,
    AporteGoalInputs,
    DolarGoalInputs,
    IFGoalInputs,
)
from backend.app.schemas.dto.goal.alocacao_shape_conversion import (
    compute_alocacao_derived_v2,
    convert_alocacao_inputs_to_v2,
)
from backend.app.services import goal_service

# Tabela canônica `target_field → (goal_type, param_path)`.
PROJECTIONS: dict[str, tuple[str, str]] = {
    "goal.if.trs_pct": ("INDEPENDENCIA_FINANCEIRA", "trs_pct"),
    "goal.if.renda_passiva_mensal_brl": ("INDEPENDENCIA_FINANCEIRA", "renda_passiva_mensal_brl"),
    "goal.if.horizonte_anos": ("INDEPENDENCIA_FINANCEIRA", "horizonte_anos"),
    "goal.aporte.meta_aporte_mensal_brl": ("APORTE_MENSAL", "meta_aporte_mensal_brl"),
    "goal.dolar.meta_usd": ("DOLARIZACAO", "meta_usd"),
    "goal.dolar.aporte_mensal_brl": ("DOLARIZACAO", "aporte_mensal_brl"),
}


async def project_decision_to_goal(
    decision: Decision,
    *,
    db: AsyncSession,
    actor: str | None = None,
) -> Goal | None:
    """Cria nova versão do Goal a partir do `target_field` da Decision.

    Retorna o Goal criado, ou ``None`` se ``target_field`` for ``None``
    (Decisions sem alvo continuam terminais — comportamento preservado).
    Lança ``ValidationError`` em caso de mapping/parsing inválido.
    """
    if decision.target_field is None:
        return None
    goal_type, param_path = _resolve_projection(decision.target_field)
    new_value = _parse_value(
        decision.target_value, decision.target_value_type, decision.target_field
    )
    return await _apply_projection(
        decision=decision,
        goal_type=goal_type,
        param_path=param_path,
        new_value=new_value,
        db=db,
        actor=actor,
    )


def _resolve_projection(target_field: str) -> tuple[str, str]:
    if target_field not in PROJECTIONS:
        raise ValidationError(
            f"target_field={target_field!r} não tem projection registrada — "
            f"adicione em backend.app.services.decision_goal_projection.PROJECTIONS",
            code="projection_not_registered",
        )
    return PROJECTIONS[target_field]


def _parse_value(raw: str | None, type_hint: str | None, field: str) -> Any:
    if raw is None:
        raise ValidationError(
            f"target_value ausente para {field!r} (target_field populado exige target_value)",
            code="target_value_required",
        )
    if type_hint is None:
        raise ValidationError(
            f"target_value_type ausente para {field!r}",
            code="target_value_type_required",
        )
    try:
        if type_hint == "pct":
            return float(raw)
        if type_hint == "brl":
            return Decimal(str(raw))
        if type_hint == "int":
            return int(raw)
        if type_hint == "str":
            return str(raw)
    except (InvalidOperation, ValueError) as exc:
        raise ValidationError(
            f"target_value={raw!r} não parseável como {type_hint!r}: {exc}",
            code="target_value_parse_error",
        ) from exc
    raise ValidationError(
        f"target_value_type={type_hint!r} inválido — use pct|brl|int|str",
        code="target_value_type_invalid",
    )


async def _apply_projection(
    *,
    decision: Decision,
    goal_type: str,
    param_path: str,
    new_value: Any,
    db: AsyncSession,
    actor: str | None,
) -> Goal:
    """Lê Goal vigente, aplica patch no param_path, cria nova versão."""
    repo = GoalRepository(db)
    current = await repo.get_active_by_type(decision.workspace_id, goal_type)
    if current is None:
        raise ValidationError(
            f"Não há Goal {goal_type!r} vigente para workspace {decision.workspace_id} — "
            f"crie a primeira versão antes de tentar projetar uma Decision",
            code="goal_not_found",
        )
    inputs = _patch_goal_inputs(current, goal_type, param_path, new_value)
    notes = (
        f"Derivada da Decision {decision.code} ({decision.id})"
        if decision.code
        else f"Derivada da Decision {decision.id}"
    )
    return await goal_service.create_goal_version(
        decision.workspace_id,
        goal_type,
        inputs=inputs,
        derived=_compute_derived(goal_type, inputs),
        db=db,
        created_by=None,
        notes=notes,
        is_template=False,
    )


def _patch_goal_inputs(current: Goal, goal_type: str, param_path: str, new_value: Any):
    """Aplica patch em inputs — devolve Pydantic model do tipo correto."""
    base_inputs = (current.params_json or {}).get("inputs") or {}
    if goal_type == "ALOCACAO_ALVO":
        # converter-antes-de-patchar: row vigente pode ser v1/órfã
        # (ADR-141 emenda item 5); patch sempre opera no shape v2.
        convertido, _ = convert_alocacao_inputs_to_v2(base_inputs)
        patched = {**(convertido or {}), param_path: new_value}
        return AlocacaoGoalInputsV2.model_validate(patched)
    patched = {**base_inputs, param_path: new_value}
    if goal_type == "INDEPENDENCIA_FINANCEIRA":
        return IFGoalInputs.model_validate(patched)
    if goal_type == "APORTE_MENSAL":
        return AporteGoalInputs.model_validate(patched)
    if goal_type == "DOLARIZACAO":
        return DolarGoalInputs.model_validate(patched)
    raise ValidationError(
        f"goal_type={goal_type!r} não suporta projection",
        code="goal_type_not_projectable",
    )


def _compute_derived(goal_type: str, inputs):
    """Re-compute derived (`derived_json`) via funções puras existentes."""
    if goal_type == "INDEPENDENCIA_FINANCEIRA":
        return goal_service.compute_if_derived(inputs)
    if goal_type == "APORTE_MENSAL":
        return goal_service.compute_aporte_derived(inputs)
    if goal_type == "DOLARIZACAO":
        return goal_service.compute_dolar_derived(inputs)
    if goal_type == "ALOCACAO_ALVO":
        return compute_alocacao_derived_v2(inputs)
    raise ValidationError(f"goal_type={goal_type!r} sem compute", code="no_compute")
