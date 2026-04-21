"""DTOs do goal type ``APORTE_MENSAL``.

Meta de aporte mensal com distribuição opcional por destino. Se
``distribuicao`` não estiver vazio, a soma dos valores tem que bater
com ``meta_aporte_mensal_brl`` (validador de domínio no Inputs).
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator

from backend.app.schemas.dto.goal.base import GoalResponseBase


class AporteGoalInputs(BaseModel):
    """Inputs do usuário para estratégia de aportes mensais."""

    meta_aporte_mensal_brl: float = Field(
        ..., gt=0, description="Meta de aporte mensal total em BRL.",
    )
    dia_aporte: int = Field(
        5, ge=1, le=28, description="Dia do mês para o aporte (1-28).",
    )
    periodo_inicio: str = Field(
        "Imediato", description="Quando iniciar (ex: 'Imediato', 'Mai/2026').",
    )
    distribuicao: dict[str, float] = Field(
        default_factory=dict,
        description="Mapa destino → valor BRL. Se não-vazio, soma deve == meta.",
    )

    @model_validator(mode="after")
    def _validar_distribuicao(self):
        if self.distribuicao:
            soma = sum(self.distribuicao.values())
            if abs(soma - self.meta_aporte_mensal_brl) > 0.01:
                raise ValueError(
                    f"Soma da distribuição ({soma:.2f}) difere da meta "
                    f"({self.meta_aporte_mensal_brl:.2f})."
                )
        return self


class AporteGoalDerived(BaseModel):
    """Valores derivados de aportes."""

    aporte_anual_brl: float = Field(
        ..., description="Meta anualizada (meta_mensal × 12).",
    )
    distribuicao_pct: dict[str, float] = Field(
        default_factory=dict,
        description="Percentual de cada destino sobre o total.",
    )


class AporteGoalComputeRequest(BaseModel):
    inputs: AporteGoalInputs


class AporteGoalComputeResponse(BaseModel):
    derived: AporteGoalDerived


class AporteGoalUpsertCommand(BaseModel):
    """Comando para criar nova versão da meta de aportes."""

    inputs: AporteGoalInputs
    notes: Optional[str] = Field(None, max_length=1000)


class AporteGoalResponse(GoalResponseBase):
    type: Literal["APORTE_MENSAL"] = "APORTE_MENSAL"
    inputs: AporteGoalInputs
    derived: AporteGoalDerived


class AporteGoalHistoryResponse(BaseModel):
    goals: list[AporteGoalResponse]
    total: int
