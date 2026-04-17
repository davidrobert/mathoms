"""E7-review output schema — holistic financial review by LLM consultant persona."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class ReviewInsight(BaseModel):
    """A single insight from the financial review."""
    category: str = Field(..., description="Category: patrimonio, fluxo_caixa, investimentos, endividamento, planejamento, score")
    severity: str = Field(..., description="Severity: info, attention, warning, critical")
    title: str = Field(..., max_length=120, description="Short insight title — até 120 caracteres")
    description: str = Field(..., max_length=600, description="Explicação objetiva — até 100 palavras (máx 600 caracteres)")
    recommendation: Optional[str] = Field(None, max_length=400, description="Ação concreta — até 60 palavras (máx 400 caracteres)")


class ScoreAdjustment(BaseModel):
    """An adjustment to the financial score based on qualitative review."""
    factor: str = Field(..., max_length=80, description="Factor being adjusted")
    original_value: Optional[float] = None
    adjustment: float = Field(..., description="Adjustment amount (positive or negative)")
    reason: str = Field(..., max_length=300, description="Justificativa — até 50 palavras (máx 300 caracteres)")


class NarrativeSection(BaseModel):
    """A narrative section for the report."""
    section_key: str = Field(..., description="Section identifier (e.g. 'resumo_executivo', 'patrimonio_analise')")
    title: str = Field(..., max_length=100, description="Section title — até 100 caracteres")
    content: str = Field(..., max_length=2000, description="Texto narrativo em markdown simples — até 300 palavras (máx 2000 caracteres). Sem listas gigantes, sem tabelas.")


class E7ReviewOutput(BaseModel):
    """Structured output for E7-review — holistic financial review."""
    insights: list[ReviewInsight] = Field(default_factory=list, max_length=8, description="Até 8 insights priorizados por severidade")
    recommendations: list[str] = Field(default_factory=list, max_length=6, description="Até 6 recomendações — cada uma com até 200 caracteres, ordenadas por impacto")
    score_adjustments: list[ScoreAdjustment] = Field(default_factory=list, max_length=5, description="Até 5 ajustes qualitativos ao score")
    narrative_sections: list[NarrativeSection] = Field(default_factory=list, max_length=5, description="Até 5 seções narrativas")
    overall_assessment: str = Field(..., max_length=2500, description="Avaliação geral — 3 a 5 parágrafos (máx 2500 caracteres)")
    risk_level: str = Field(..., description="Overall risk level: low, moderate, high, critical")
    confidence: float = Field(..., ge=0.0, le=1.0)
