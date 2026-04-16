"""Pydantic schemas dos endpoints de Goal (ADR-073).

Espelha o JSON Schema canônico em `config/schemas/goal.if.schema.json`
para o tipo `INDEPENDENCIA_FINANCEIRA`. Outros tipos (aporte mensal,
dolarização, alocação) serão adicionados em F8.5+.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, ConfigDict


# ─── Inputs e derivados do tipo IF ─────────────────────────────────────

class IFGoalInputs(BaseModel):
    """Inputs que o usuário fornece para a meta de Independência
    Financeira. Corresponde a `params_json.inputs` no DB."""

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
    """Valores derivados pela função pura `compute_if_derived`. Nunca
    digitados pelo usuário — sempre calculados server-side."""

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
            "Preenchido quando `patrimonio_atual_brl` é conhecido: aporte mensal "
            "para fechar a meta considerando o patrimônio hoje projetado até o fim "
            "do horizonte. UI deve preferir este valor ao baseline quando presente."
        ),
    )
    patrimonio_atual_utilizado_brl: Optional[float] = Field(
        None,
        ge=0,
        description="Patrimônio usado no cálculo de `aporte_mensal_com_patrimonio_atual_brl`.",
    )


# ─── Payload de persistência e preview ─────────────────────────────────

class IFGoalComputeRequest(BaseModel):
    """Request do endpoint dry-run `/goals/if/compute`. Não persiste."""

    inputs: IFGoalInputs
    patrimonio_atual_brl: Optional[float] = Field(
        None,
        ge=0,
        description="Opcional. Se fornecido: progresso (percentual e faltante) e "
        "`aporte_mensal_com_patrimonio_atual_brl` nos derivados.",
    )


class IFGoalComputeResponse(BaseModel):
    """Response do dry-run. Devolve derivados + contexto de progresso."""

    derived: IFGoalDerived
    percentual_conquistado: Optional[float] = Field(
        None,
        description="Só presente se `patrimonio_atual_brl` foi enviado.",
    )
    faltante_brl: Optional[float] = None


class IFGoalUpsertRequest(BaseModel):
    """Request para criar nova versão do Goal IF (PUT)."""

    inputs: IFGoalInputs
    notes: Optional[str] = Field(
        None,
        max_length=1000,
        description="Motivo da mudança. Livre — ex: 'revisão anual', 'mudou horizonte'.",
    )


class IFGoalResponse(BaseModel):
    """Representação do Goal IF vigente ou histórico."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    workspace_id: str
    type: Literal["INDEPENDENCIA_FINANCEIRA"] = "INDEPENDENCIA_FINANCEIRA"
    inputs: IFGoalInputs
    derived: IFGoalDerived
    effective_from: date
    effective_to: Optional[date] = None
    is_template: bool = False
    notes: Optional[str] = None
    created_by: Optional[str] = None
    created_by_name: Optional[str] = Field(
        None,
        description=(
            "Nome humano do autor da versão (join com users.full_name). "
            "Usado para atribuição de autoria na UI (F9)."
        ),
    )
    created_at: datetime
    updated_at: datetime


class IFGoalHistoryResponse(BaseModel):
    """Histórico ordenado cronologicamente (vigente primeiro)."""

    goals: list[IFGoalResponse]
    total: int
