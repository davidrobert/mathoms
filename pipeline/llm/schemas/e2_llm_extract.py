"""E2-llm output schema — transactions/investments extracted from docs without deterministic parser."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Optional

from pydantic import BaseModel, Field, field_validator


def _coerce_decimal(v):
    """Boundary LLM monetário = ``Decimal`` (ADR-090, A33.l1): aceita ``int|str|float``
    via ``Decimal(str(v))`` — o prompt v1.3.0 pede string decimal, mas number JSON de
    respostas antigas/reask não pode brickar a extração."""
    if v is None:
        return None
    if isinstance(v, Decimal):
        return v
    if isinstance(v, (int, float, str)):
        try:
            return Decimal(str(v))
        except InvalidOperation as exc:
            raise ValueError(
                f"E2-llm: valor monetário inválido — esperado string decimal "
                f"'1234.56', recebido {type(v).__name__}={v!r}"
            ) from exc
    raise TypeError(f"E2-llm: não consigo coerce {type(v).__name__}={v!r} para Decimal")


class ExtractedTransaction(BaseModel):
    """A single transaction extracted by LLM from an unstructured document."""

    date: str = Field(..., description="Transaction date in YYYY-MM-DD format")
    description: str = Field(..., description="Transaction description/memo")
    amount: Decimal = Field(
        ...,
        description=(
            "Transaction amount in BRL as decimal string (e.g. '-150.00'; "
            "positive = credit, negative = debit)"
        ),
    )
    category_hint: Optional[str] = Field(
        None,
        description=(
            "Suggested category code (ADR-242 vocabulário canônico). Use SOMENTE "
            "um dos valores: salario, pro_labore_pj, aluguel_recebido, "
            "rendimento_renda_fixa, dividendo_jcp, ganho_capital_resgate, "
            "moradia_financiamento_juros, moradia_financiamento_amortizacao, "
            "moradia_aluguel_pago, moradia_outros, alimentacao, transporte, "
            "saude, educacao, lazer_assinatura, vestuario_pessoal, "
            "aporte_investimento, seguro_previdencia, imposto_pago, "
            "juros_divida_consumo, transferencia_interna, info_fiscal_anual. "
            "Marque info_fiscal_anual para linhas de informe IR acumulado "
            "anual (não evento mensal de caixa) — evita double-counting."
        ),
    )
    balance_after: Optional[Decimal] = Field(
        None,
        description="Account balance after this transaction as decimal string, if available",
    )

    _coerce_money = field_validator("amount", "balance_after", mode="before")(_coerce_decimal)


class ExtractedInvestment(BaseModel):
    """An investment position extracted from a report without deterministic parser."""

    type: str = Field(
        ...,
        description="Investment type: cdb, lci, lca, fundo, acao, tesouro, poupanca, previdencia, outros",
    )
    institution: str = Field(..., description="Canonical bank code")
    description: str = Field(..., description="Investment description/name")
    value_brl: Decimal = Field(
        ..., description="Current value in BRL as decimal string (e.g. '25000.00')"
    )
    applied_date: Optional[str] = Field(
        None, description="Application date in YYYY-MM-DD, if available"
    )
    maturity_date: Optional[str] = Field(
        None, description="Maturity date in YYYY-MM-DD, if applicable"
    )
    rate: Optional[str] = Field(None, description="Rate description (e.g. '100% CDI', 'IPCA+5.5%')")
    member_key: Optional[str] = Field(None, description="Owning family member key")

    _coerce_value = field_validator("value_brl", mode="before")(_coerce_decimal)


class LLMExtractOutput(BaseModel):
    """Structured output for E2-llm — extraction from documents without deterministic parsers."""

    source_file: str = Field(..., description="Original filename that was processed")
    institution: str = Field(..., description="Canonical bank/institution code")
    document_type: str = Field(
        ..., description="Document type: investment_report, informe_rendimentos, extrato, other"
    )
    period: Optional[str] = Field(None, description="Period in YYYYMM format if identifiable")
    member_key: Optional[str] = Field(None, description="Owning family member key if identifiable")
    currency: str = Field(default="BRL", description="Currency code")
    transactions: list[ExtractedTransaction] = Field(default_factory=list)
    investments: list[ExtractedInvestment] = Field(default_factory=list)
    confidence: float = Field(..., ge=0.0, le=1.0)
    notes: Optional[str] = None
