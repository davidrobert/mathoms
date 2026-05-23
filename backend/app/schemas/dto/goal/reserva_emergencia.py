"""DTOs do goal type ``RESERVA_EMERGENCIA`` (ADR-263): meses_alvo × despesa_essencial_mensal_brl."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator

from backend.app.schemas.dto.goal.base import GoalResponseBase
from backend.app.schemas.money import MoneyBRL


class ReservaEmergenciaGoalInputs(BaseModel):
    """Inputs do usuário. INV1: `meses_alvo ∈ [3, 18]`; user_declared exige despesa."""

    meses_alvo: int = Field(
        ...,
        ge=3,
        le=18,
        description="Meses de despesa essencial cobertos (3 a 18; default sugerido 6).",
    )
    fonte_despesa_essencial: Literal["e5_derived", "user_declared"] = Field(
        ...,
        description="Origem do denominador. 'e5_derived' lê de E5; 'user_declared' usa o campo declarado.",
    )
    despesa_essencial_mensal_brl_declared: Optional[MoneyBRL] = Field(
        None,
        gt=0,
        description="Obrigatório se fonte=user_declared. Despesa essencial mensal declarada em BRL.",
    )
    rationale: Optional[str] = Field(
        None,
        max_length=500,
        description="Justificativa metodológica opcional.",
    )

    @model_validator(mode="after")
    def _require_declared_when_user_source(self):
        if (
            self.fonte_despesa_essencial == "user_declared"
            and self.despesa_essencial_mensal_brl_declared is None
        ):
            raise ValueError(
                "despesa_essencial_mensal_brl_declared é obrigatória quando "
                "fonte_despesa_essencial=user_declared"
            )
        return self


class ReservaEmergenciaGoalDerived(BaseModel):
    """Valores derivados da reserva."""

    valor_alvo_brl: MoneyBRL = Field(
        ...,
        ge=0,
        description="despesa_essencial_mensal_brl × meses_alvo.",
    )
    valor_atual_brl: MoneyBRL = Field(
        ...,
        ge=0,
        description="Patrimônio acessível destinado a reserva (E5).",
    )
    cobertura_meses_atual: float = Field(
        ...,
        ge=0,
        description="valor_atual_brl / despesa_essencial_mensal_brl.",
    )
    gap_brl: MoneyBRL = Field(
        ...,
        description="valor_alvo_brl - valor_atual_brl (pode ser negativo se excede alvo).",
    )
    despesa_essencial_mensal_brl: MoneyBRL = Field(
        ...,
        gt=0,
        description="Denominador efetivamente usado.",
    )
    source_e5_run_id: Optional[str] = Field(
        None,
        description="Run id de E5 consumido (null se fonte=user_declared).",
    )


class ReservaEmergenciaGoalComputeRequest(BaseModel):
    """Compute request — caller fornece despesa de E5 se fonte=e5_derived."""

    inputs: ReservaEmergenciaGoalInputs
    despesa_essencial_mensal_brl_from_e5: Optional[MoneyBRL] = Field(
        None,
        gt=0,
        description="Despesa essencial derivada de E5. Obrigatória se inputs.fonte=e5_derived.",
    )
    patrimonio_acessivel_brl: Optional[MoneyBRL] = Field(
        None,
        ge=0,
        description="Patrimônio destinado a reserva (E5). Default 0 se ausente.",
    )
    source_e5_run_id: Optional[str] = Field(
        None,
        description="Run id de E5 consumido. Persistido em derived.source_e5_run_id.",
    )


class ReservaEmergenciaGoalComputeResponse(BaseModel):
    derived: ReservaEmergenciaGoalDerived


class ReservaEmergenciaGoalUpsertCommand(BaseModel):
    """Comando para criar nova versão da meta de reserva."""

    inputs: ReservaEmergenciaGoalInputs
    notes: Optional[str] = Field(None, max_length=1000)


class ReservaEmergenciaGoalResponse(GoalResponseBase):
    type: Literal["RESERVA_EMERGENCIA"] = "RESERVA_EMERGENCIA"
    inputs: ReservaEmergenciaGoalInputs
    derived: ReservaEmergenciaGoalDerived


class ReservaEmergenciaGoalHistoryResponse(BaseModel):
    goals: list[ReservaEmergenciaGoalResponse]
    total: int
