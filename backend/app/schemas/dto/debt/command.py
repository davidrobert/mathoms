"""Command DTOs do agregado ``Debt`` — dinheiro em string decimal (ADR-090); caller converte para cents."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator

from backend.app.models.debt import VALID_DEBT_SOURCES, VALID_DEBT_TIPOS

DebtTipo = Literal[
    "financiamento_imobiliario",
    "consignado",
    "cdc",
    "cartao_rotativo",
    "rotativo",
    "outro",
]

DebtSource = Literal[
    "baseline_irpf_migration",
    "user_declared",
    "open_banking_futuro",
]

# Sanity-check: types acima espelham VALID_DEBT_* do model.
assert set(VALID_DEBT_TIPOS) == set(DebtTipo.__args__)  # type: ignore[attr-defined]
assert set(VALID_DEBT_SOURCES) == set(DebtSource.__args__)  # type: ignore[attr-defined]


class _DebtBase(BaseModel):
    """Campos compartilhados entre Create e Update."""

    family_member_id: Optional[str] = Field(None, max_length=36)
    property_id: Optional[str] = Field(None, max_length=36)
    tipo: DebtTipo
    descricao: Optional[str] = Field(None, max_length=2000)
    saldo_devedor_brl: Decimal = Field(
        ..., ge=0, description="Saldo devedor em BRL (string decimal)."
    )
    parcela_mensal_brl: Optional[Decimal] = Field(None, ge=0)
    taxa_juros_aa: Optional[Decimal] = Field(None, ge=0, le=Decimal("999.99"))
    prazo_meses_restantes: Optional[int] = Field(None, ge=0, le=600)
    data_contratacao: Optional[date] = None
    percentual_atribuicao_imovel: Optional[Decimal] = Field(
        None,
        gt=0,
        le=100,
        description="Percentual 0 < pct ≤ 100; default 100% quando property_id setado.",
    )

    @model_validator(mode="after")
    def _check_identity(self) -> "_DebtBase":
        """Espelha CHECK ``chk_debt_identity`` — exige um de family_member_id/property_id/descricao."""
        if (
            self.family_member_id is None
            and self.property_id is None
            and (self.descricao is None or not self.descricao.strip())
        ):
            raise ValueError(
                "Debt exige ao menos uma identidade: family_member_id, property_id ou descricao."
            )
        return self


class DebtCreate(_DebtBase):
    """Input de criação; ``source`` default ``user_declared``."""

    source: DebtSource = "user_declared"
    migration_source_key: Optional[str] = Field(None, max_length=64)
    needs_review: bool = False


class DebtUpdate(BaseModel):
    """Input de update PATCH; ``workspace_id``/``source``/``migration_source_key`` imutáveis."""

    family_member_id: Optional[str] = Field(None, max_length=36)
    property_id: Optional[str] = Field(None, max_length=36)
    tipo: Optional[DebtTipo] = None
    descricao: Optional[str] = Field(None, max_length=2000)
    saldo_devedor_brl: Optional[Decimal] = Field(None, ge=0)
    parcela_mensal_brl: Optional[Decimal] = Field(None, ge=0)
    taxa_juros_aa: Optional[Decimal] = Field(None, ge=0, le=Decimal("999.99"))
    prazo_meses_restantes: Optional[int] = Field(None, ge=0, le=600)
    data_contratacao: Optional[date] = None
    percentual_atribuicao_imovel: Optional[Decimal] = Field(None, gt=0, le=100)
    needs_review: Optional[bool] = None
