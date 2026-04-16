"""Pydantic schemas dos endpoints de Goal (ADR-073).

Tipos implementados:
- INDEPENDENCIA_FINANCEIRA (F8.1)
- APORTE_MENSAL (F8.5)
- DOLARIZACAO (F8.5)
- ALOCACAO_ALVO (F8.5)
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal, Optional, Union

from pydantic import BaseModel, Field, ConfigDict, model_validator


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


# ─── Base compartilhada para respostas ────────────────────────────────


class _GoalResponseBase(BaseModel):
    """Campos comuns a todas as respostas de Goal."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    workspace_id: str
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


class IFGoalResponse(_GoalResponseBase):
    """Representação do Goal IF vigente ou histórico."""

    type: Literal["INDEPENDENCIA_FINANCEIRA"] = "INDEPENDENCIA_FINANCEIRA"
    inputs: IFGoalInputs
    derived: IFGoalDerived


class IFGoalHistoryResponse(BaseModel):
    """Histórico ordenado cronologicamente (vigente primeiro)."""

    goals: list[IFGoalResponse]
    total: int


# ─── APORTE_MENSAL (F8.5) ────────────────────────────────────────────


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


class AporteGoalUpsertRequest(BaseModel):
    inputs: AporteGoalInputs
    notes: Optional[str] = Field(None, max_length=1000)


class AporteGoalResponse(_GoalResponseBase):
    type: Literal["APORTE_MENSAL"] = "APORTE_MENSAL"
    inputs: AporteGoalInputs
    derived: AporteGoalDerived


class AporteGoalHistoryResponse(BaseModel):
    goals: list[AporteGoalResponse]
    total: int


# ─── DOLARIZACAO (F8.5) ──────────────────────────────────────────────


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


class DolarGoalUpsertRequest(BaseModel):
    inputs: DolarGoalInputs
    notes: Optional[str] = Field(None, max_length=1000)


class DolarGoalResponse(_GoalResponseBase):
    type: Literal["DOLARIZACAO"] = "DOLARIZACAO"
    inputs: DolarGoalInputs
    derived: DolarGoalDerived


class DolarGoalHistoryResponse(BaseModel):
    goals: list[DolarGoalResponse]
    total: int


# ─── ALOCACAO_ALVO (F8.5) ────────────────────────────────────────────


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
        soma = (self.renda_fixa_pct + self.acoes_pct
                + self.imoveis_reits_pct + self.liquidez_usd_pct)
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


class AlocacaoGoalUpsertRequest(BaseModel):
    inputs: AlocacaoGoalInputs
    notes: Optional[str] = Field(None, max_length=1000)


class AlocacaoGoalResponse(_GoalResponseBase):
    type: Literal["ALOCACAO_ALVO"] = "ALOCACAO_ALVO"
    inputs: AlocacaoGoalInputs
    derived: AlocacaoGoalDerived


class AlocacaoGoalHistoryResponse(BaseModel):
    goals: list[AlocacaoGoalResponse]
    total: int
