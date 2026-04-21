"""DTOs do goal type ``ALOCACAO_ALVO``.

Alocação-alvo de ativos em 4 classes (renda fixa, ações, imóveis/REITs,
liquidez USD). A soma dos 4 percentuais tem que fechar 100% (validador
de domínio no Inputs).
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator

from backend.app.schemas.dto.goal.base import GoalResponseBase


class AlocacaoGoalInputs(BaseModel):
    """Inputs do usuário para alocação-alvo de ativos."""

    renda_fixa_pct: float = Field(..., ge=0, le=100)
    acoes_pct: float = Field(..., ge=0, le=100)
    imoveis_reits_pct: float = Field(..., ge=0, le=100)
    liquidez_usd_pct: float = Field(..., ge=0, le=100)
    instrumentos_rf: str = Field(
        "", description="Instrumentos de renda fixa preferidos.",
    )
    instrumentos_rv: str = Field(
        "", description="Instrumentos de renda variável preferidos.",
    )
    rebalanceamento: str = Field(
        "anual", description="Frequência de rebalanceamento.",
    )

    @model_validator(mode="after")
    def _validar_soma_100(self):
        soma = (
            self.renda_fixa_pct
            + self.acoes_pct
            + self.imoveis_reits_pct
            + self.liquidez_usd_pct
        )
        if abs(soma - 100.0) > 0.01:
            raise ValueError(
                f"Percentuais devem somar 100% (atual: {soma:.2f}%)."
            )
        return self


class AlocacaoGoalDerived(BaseModel):
    soma_percentuais: float = Field(
        ..., description="Soma dos 4 percentuais (deve ser 100).",
    )


class AlocacaoGoalComputeRequest(BaseModel):
    inputs: AlocacaoGoalInputs


class AlocacaoGoalComputeResponse(BaseModel):
    derived: AlocacaoGoalDerived
    valido: bool = Field(
        ..., description="True se soma_percentuais == 100.",
    )


class AlocacaoGoalUpsertCommand(BaseModel):
    """Comando para criar nova versão da alocação-alvo."""

    inputs: AlocacaoGoalInputs
    notes: Optional[str] = Field(None, max_length=1000)


class AlocacaoGoalResponse(GoalResponseBase):
    type: Literal["ALOCACAO_ALVO"] = "ALOCACAO_ALVO"
    inputs: AlocacaoGoalInputs
    derived: AlocacaoGoalDerived


class AlocacaoGoalHistoryResponse(BaseModel):
    goals: list[AlocacaoGoalResponse]
    total: int
