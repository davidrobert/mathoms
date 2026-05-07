"""Command DTOs do agregado ``Risk`` (ADR-178).

Money em ``impact_brl_cents`` no DB; wire em string decimal ``impact_brl``
(ADR-090). Conversão centralizada em ``mapper.brl_to_cents``.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.app.models.risk import (
    VALID_RISK_IMPACT_LEVELS,
    VALID_RISK_PROBABILITIES,
    VALID_RISK_STATUSES,
)


class RiskCreateCommand(BaseModel):
    """Cria novo ``Risk`` (status default = ``Ativo``)."""

    model_config = ConfigDict(extra="forbid")

    code: str = Field(..., min_length=1, max_length=64)
    name: str = Field(..., min_length=1, max_length=200)
    rationale: str = Field(..., min_length=10)
    probability: Optional[str] = None
    impact_level: str = Field(..., min_length=1)
    impact_brl: Optional[Decimal] = Field(
        None, description="Impacto em BRL (string decimal). Convertido para cents."
    )
    status: str = "Ativo"
    mitigations_decision_ids: list[str] = Field(default_factory=list)

    @field_validator("probability")
    @classmethod
    def _validate_probability(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if v not in VALID_RISK_PROBABILITIES:
            raise ValueError(
                f"probability inválida: {v!r}; aceitos: {sorted(VALID_RISK_PROBABILITIES)}"
            )
        return v

    @field_validator("impact_level")
    @classmethod
    def _validate_impact_level(cls, v: str) -> str:
        if v not in VALID_RISK_IMPACT_LEVELS:
            raise ValueError(
                f"impact_level inválido: {v!r}; aceitos: {sorted(VALID_RISK_IMPACT_LEVELS)}"
            )
        return v

    @field_validator("status")
    @classmethod
    def _validate_status(cls, v: str) -> str:
        if v not in VALID_RISK_STATUSES:
            raise ValueError(f"status inválido: {v!r}; aceitos: {sorted(VALID_RISK_STATUSES)}")
        return v


class RiskUpdateCommand(BaseModel):
    """Atualiza campos editoriais do Risk."""

    model_config = ConfigDict(extra="forbid")

    name: Optional[str] = Field(None, min_length=1, max_length=200)
    rationale: Optional[str] = Field(None, min_length=10)
    probability: Optional[str] = None
    impact_level: Optional[str] = None
    impact_brl: Optional[Decimal] = None
    status: Optional[str] = None

    @field_validator("probability")
    @classmethod
    def _validate_probability(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if v not in VALID_RISK_PROBABILITIES:
            raise ValueError(
                f"probability inválida: {v!r}; aceitos: {sorted(VALID_RISK_PROBABILITIES)}"
            )
        return v

    @field_validator("impact_level")
    @classmethod
    def _validate_impact_level(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if v not in VALID_RISK_IMPACT_LEVELS:
            raise ValueError(
                f"impact_level inválido: {v!r}; aceitos: {sorted(VALID_RISK_IMPACT_LEVELS)}"
            )
        return v

    @field_validator("status")
    @classmethod
    def _validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if v not in VALID_RISK_STATUSES:
            raise ValueError(f"status inválido: {v!r}; aceitos: {sorted(VALID_RISK_STATUSES)}")
        return v


class RiskMitigationLinkCommand(BaseModel):
    """Adiciona uma Decision como mitigação do Risk."""

    model_config = ConfigDict(extra="forbid")

    decision_id: str = Field(..., min_length=36, max_length=36)
