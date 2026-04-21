"""DTOs do goal type ``DOLARIZACAO``.

Meta de acúmulo em USD com aporte mensal em BRL. O câmbio pode ser
passado no request de compute (``cambio_brl_usd`` override); se
omitido, o service usa ``DEFAULT_CAMBIO_BRL_USD``.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

from backend.app.schemas.dto.goal.base import GoalResponseBase


class DolarGoalInputs(BaseModel):
    """Inputs do usuário para meta de dolarização."""

    meta_usd: float = Field(
        ..., gt=0, description="Meta de acumulação em USD.",
    )
    aporte_mensal_brl: float = Field(
        ..., gt=0, description="Aporte mensal em BRL para conversão.",
    )


class DolarGoalDerived(BaseModel):
    """Valores derivados de dolarização."""

    horizonte_estimado_meses: float = Field(
        ..., ge=0, description="Meses estimados para atingir meta_usd.",
    )


class DolarGoalComputeRequest(BaseModel):
    inputs: DolarGoalInputs
    cambio_brl_usd: Optional[float] = Field(
        None, gt=0,
        description="Câmbio BRL/USD override. Se omitido, usa default (5.70).",
    )


class DolarGoalComputeResponse(BaseModel):
    derived: DolarGoalDerived
    cambio_utilizado: float = Field(
        ..., description="Câmbio BRL/USD efetivamente usado no cálculo.",
    )


class DolarGoalUpsertCommand(BaseModel):
    """Comando para criar nova versão da meta de dolarização."""

    inputs: DolarGoalInputs
    notes: Optional[str] = Field(None, max_length=1000)


class DolarGoalResponse(GoalResponseBase):
    type: Literal["DOLARIZACAO"] = "DOLARIZACAO"
    inputs: DolarGoalInputs
    derived: DolarGoalDerived


class DolarGoalHistoryResponse(BaseModel):
    goals: list[DolarGoalResponse]
    total: int
