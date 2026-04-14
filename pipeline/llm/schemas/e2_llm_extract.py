"""E2-llm output schema — transactions/investments extracted from docs without deterministic parser."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class ExtractedTransaction(BaseModel):
    """A single transaction extracted by LLM from an unstructured document."""
    date: str = Field(..., description="Transaction date in YYYY-MM-DD format")
    description: str = Field(..., description="Transaction description/memo")
    amount: float = Field(..., description="Transaction amount in BRL (positive = credit, negative = debit)")
    category_hint: Optional[str] = Field(None, description="Suggested category code if identifiable")
    balance_after: Optional[float] = Field(None, description="Account balance after this transaction, if available")


class ExtractedInvestment(BaseModel):
    """An investment position extracted from a report without deterministic parser."""
    type: str = Field(..., description="Investment type: cdb, lci, lca, fundo, acao, tesouro, poupanca, previdencia, outros")
    institution: str = Field(..., description="Canonical bank code")
    description: str = Field(..., description="Investment description/name")
    value_brl: float = Field(..., description="Current value in BRL")
    applied_date: Optional[str] = Field(None, description="Application date in YYYY-MM-DD, if available")
    maturity_date: Optional[str] = Field(None, description="Maturity date in YYYY-MM-DD, if applicable")
    rate: Optional[str] = Field(None, description="Rate description (e.g. '100% CDI', 'IPCA+5.5%')")
    member_key: Optional[str] = Field(None, description="Owning family member key")


class LLMExtractOutput(BaseModel):
    """Structured output for E2-llm — extraction from documents without deterministic parsers."""
    source_file: str = Field(..., description="Original filename that was processed")
    institution: str = Field(..., description="Canonical bank/institution code")
    document_type: str = Field(..., description="Document type: investment_report, informe_rendimentos, extrato, other")
    period: Optional[str] = Field(None, description="Period in YYYYMM format if identifiable")
    member_key: Optional[str] = Field(None, description="Owning family member key if identifiable")
    currency: str = Field(default="BRL", description="Currency code")
    transactions: list[ExtractedTransaction] = Field(default_factory=list)
    investments: list[ExtractedInvestment] = Field(default_factory=list)
    confidence: float = Field(..., ge=0.0, le=1.0)
    notes: Optional[str] = None
