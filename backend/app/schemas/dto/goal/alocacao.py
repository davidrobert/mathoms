"""DTOs do goal type ``ALOCACAO_ALVO`` — shapes v1 (4 buckets) e v2 (7 classes AUVP).

v1: soma dos 4 percentuais fecha 100% (validador de domínio no Inputs).
v2 (ADR-141 §Emenda 2026-07-08): 7 classes canônicas AUVP + enum de
rebalanceamento; soma dos 7 fecha 100%. Conversão v1/órfão→v2 vive em
``alocacao_migration.py``.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator

from backend.app.schemas.dto.goal.base import GoalResponseBase

RebalanceamentoModo = Literal[
    "por_aporte", "anual", "semestral", "trimestral", "trigger_5pct", "trigger_10pct"
]

ALOCACAO_V2_CLASS_FIELDS: tuple[str, ...] = (
    "rf_pos_pct",
    "rf_pre_pct",
    "rf_ipca_pct",
    "acoes_br_pct",
    "acoes_int_pct",
    "fiis_pct",
    "caixa_pct",
)


class AlocacaoGoalInputs(BaseModel):
    """Inputs do usuário para alocação-alvo de ativos."""

    renda_fixa_pct: float = Field(..., ge=0, le=100)
    acoes_pct: float = Field(..., ge=0, le=100)
    imoveis_reits_pct: float = Field(..., ge=0, le=100)
    liquidez_usd_pct: float = Field(..., ge=0, le=100)
    instrumentos_rf: str = Field(
        "",
        description="Instrumentos de renda fixa preferidos.",
    )
    instrumentos_rv: str = Field(
        "",
        description="Instrumentos de renda variável preferidos.",
    )
    rebalanceamento: str = Field(
        "anual",
        description="Frequência de rebalanceamento.",
    )

    @model_validator(mode="after")
    def _validar_soma_100(self):
        soma = self.renda_fixa_pct + self.acoes_pct + self.imoveis_reits_pct + self.liquidez_usd_pct
        if abs(soma - 100.0) > 0.01:
            raise ValueError(f"Percentuais devem somar 100% (atual: {soma:.2f}%).")
        return self


class AlocacaoGoalDerived(BaseModel):
    soma_percentuais: float = Field(
        ...,
        description="Soma dos 4 percentuais (deve ser 100).",
    )


class AlocacaoGoalInputsV2(BaseModel):
    """Inputs v2 — 7 classes AUVP (ADR-141). Soma das 7 fecha 100%."""

    rf_pos_pct: float = Field(..., ge=0, le=100)
    rf_pre_pct: float = Field(..., ge=0, le=100)
    rf_ipca_pct: float = Field(..., ge=0, le=100)
    acoes_br_pct: float = Field(..., ge=0, le=100)
    acoes_int_pct: float = Field(..., ge=0, le=100)
    fiis_pct: float = Field(..., ge=0, le=100)
    caixa_pct: float = Field(..., ge=0, le=100)
    rebalanceamento_modo: RebalanceamentoModo = Field(
        "por_aporte",
        description="Default AUVP: aporta na classe mais defasada, sem vender.",
    )
    instrumentos: Optional[dict[str, str]] = Field(
        None,
        description="Texto livre por classe — instrumentos preferenciais.",
    )

    @model_validator(mode="after")
    def _validar_soma_100(self):
        soma = sum(getattr(self, campo) for campo in ALOCACAO_V2_CLASS_FIELDS)
        if abs(soma - 100.0) > 0.01:
            raise ValueError(f"Percentuais das 7 classes devem somar 100% (atual: {soma:.2f}%).")
        return self


class AlocacaoGoalDerivedV2(BaseModel):
    """Derived write-time do goal v2 — magro (ADR-141 emenda item 4).

    O bloco rico de comparação atual-vs-alvo depende do run E5 e vive no
    bundle do relatório, não na row do goal.
    """

    soma_percentuais: float = Field(
        ...,
        description="Soma dos 7 percentuais (deve ser 100).",
    )


class AlocacaoGoalComputeRequest(BaseModel):
    inputs: AlocacaoGoalInputsV2


class AlocacaoGoalComputeResponse(BaseModel):
    derived: AlocacaoGoalDerivedV2
    valido: bool = Field(
        ...,
        description="True se soma_percentuais == 100.",
    )


class AlocacaoGoalUpsertCommand(BaseModel):
    """Comando para criar nova versão da alocação-alvo (v2 — 7 classes)."""

    inputs: AlocacaoGoalInputsV2
    notes: Optional[str] = Field(None, max_length=1000)


class AlocacaoGoalResponse(GoalResponseBase):
    """Response sempre v2 — rows v1/órfãs convertem on-read (ADR-141 emenda item 6)."""

    type: Literal["ALOCACAO_ALVO"] = "ALOCACAO_ALVO"
    inputs: AlocacaoGoalInputsV2
    derived: AlocacaoGoalDerivedV2
    converted_from: Optional[Literal["1", "orphan"]] = Field(
        None,
        description="Origem da conversão on-read; None = row já era v2.",
    )


class AlocacaoGoalHistoryResponse(BaseModel):
    goals: list[AlocacaoGoalResponse]
    total: int
