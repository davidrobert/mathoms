"""DTOs do goal type ``INDEPENDENCIA_FINANCEIRA``.

Inputs, Derived, ComputeRequest/Response, UpsertCommand, Response e
HistoryResponse — agrupados num só módulo para que mudanças no shape
do tipo fiquem localizadas.

Fórmulas dos derived são responsabilidade de ``goal_service.compute_if_derived``
(função pura, testada isoladamente).
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

from backend.app.schemas.dto.goal.base import GoalResponseBase


class IFGoalInputs(BaseModel):
    """Inputs do usuário para a meta de Independência Financeira.

    Corresponde a ``params_json.inputs`` no DB.
    """

    renda_passiva_mensal_brl: float = Field(
        ...,
        gt=0,
        le=10_000_000,
        description="Renda passiva mensal desejada em BRL (ex: 30000).",
    )
    trs_pct: float = Field(
        ...,
        gt=0,
        le=20,
        description="Taxa de Retirada Segura operacional (% ao ano). Default produto: 5.0.",
    )
    retorno_real_anual_pct: float = Field(
        ...,
        ge=0,
        le=20,
        description="Retorno real esperado (acima da inflação) ao ano. Típico: 4-7.",
    )
    horizonte_anos: int = Field(
        ...,
        ge=1,
        le=50,
        description="Horizonte em anos para atingir a meta.",
    )
    taxa_retirada_conservadora_pct: float = Field(
        4.0,
        gt=0,
        le=20,
        description="Taxa conservadora (default 4.0 — regra clássica de Trinity).",
    )


class IFGoalDerived(BaseModel):
    """Valores derivados pela função pura ``compute_if_derived``.

    Nunca digitados pelo usuário — sempre calculados server-side.
    """

    if_meta_brl: float = Field(
        ...,
        description="Patrimônio-alvo: renda_passiva × 12 / (trs_pct / 100).",
    )
    aporte_necessario_mensal_brl: float = Field(
        ...,
        ge=0,
        description=(
            "Aporte mensal constante para atingir if_meta_brl no horizonte, "
            "**assumindo patrimônio inicial zero** (referência; persistido no DB)."
        ),
    )
    if_meta_conservadora_brl: float = Field(
        ...,
        description="Patrimônio-alvo usando taxa conservadora (4% default).",
    )
    aporte_mensal_com_patrimonio_atual_brl: Optional[float] = Field(
        None,
        ge=0,
        description=(
            "Preenchido quando ``patrimonio_atual_brl`` é conhecido: aporte mensal "
            "para fechar a meta considerando o patrimônio hoje projetado até o fim "
            "do horizonte. UI deve preferir este valor ao baseline quando presente."
        ),
    )
    patrimonio_atual_utilizado_brl: Optional[float] = Field(
        None,
        ge=0,
        description="Patrimônio usado no cálculo de ``aporte_mensal_com_patrimonio_atual_brl``.",
    )


class IFGoalComputeRequest(BaseModel):
    """Request do endpoint dry-run ``/goals/if/compute``. Não persiste."""

    inputs: IFGoalInputs
    patrimonio_atual_brl: Optional[float] = Field(
        None,
        ge=0,
        description=(
            "Opcional. Se fornecido: progresso (percentual e faltante) e "
            "``aporte_mensal_com_patrimonio_atual_brl`` nos derivados."
        ),
    )


class IFGoalComputeResponse(BaseModel):
    """Response do dry-run. Devolve derivados + contexto de progresso."""

    derived: IFGoalDerived
    percentual_conquistado: Optional[float] = Field(
        None,
        description="Só presente se ``patrimonio_atual_brl`` foi enviado.",
    )
    faltante_brl: Optional[float] = None


class IFGoalUpsertCommand(BaseModel):
    """Comando para criar nova versão do Goal IF (``PUT /goals/if``)."""

    inputs: IFGoalInputs
    notes: Optional[str] = Field(
        None,
        max_length=1000,
        description="Motivo da mudança. Livre — ex: 'revisão anual', 'mudou horizonte'.",
    )


class IFGoalResponse(GoalResponseBase):
    """Representação do Goal IF vigente ou histórico."""

    type: Literal["INDEPENDENCIA_FINANCEIRA"] = "INDEPENDENCIA_FINANCEIRA"
    inputs: IFGoalInputs
    derived: IFGoalDerived


class IFGoalHistoryResponse(BaseModel):
    """Histórico ordenado cronologicamente (vigente primeiro)."""

    goals: list[IFGoalResponse]
    total: int
