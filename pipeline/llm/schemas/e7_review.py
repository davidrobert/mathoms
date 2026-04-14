"""E7-review output schema — holistic financial review by LLM consultant persona."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class ReviewInsight(BaseModel):
    """A single insight from the financial review."""
    category: str = Field(..., description="Category: patrimonio, fluxo_caixa, investimentos, endividamento, planejamento, score")
    severity: str = Field(..., description="Severity: info, attention, warning, critical")
    title: str = Field(..., description="Short insight title")
    description: str = Field(..., description="Detailed explanation")
    recommendation: Optional[str] = Field(None, description="Specific actionable recommendation")


class ScoreAdjustment(BaseModel):
    """An adjustment to the financial score based on qualitative review."""
    factor: str = Field(..., description="Factor being adjusted")
    original_value: Optional[float] = None
    adjustment: float = Field(..., description="Adjustment amount (positive or negative)")
    reason: str = Field(..., description="Justification for the adjustment")


class NarrativeSection(BaseModel):
    """A narrative section for the report."""
    section_key: str = Field(..., description="Section identifier (e.g. 'resumo_executivo', 'patrimonio_analise')")
    title: str = Field(..., description="Section title")
    content: str = Field(..., description="Narrative text content (markdown supported)")


class E7ReviewOutput(BaseModel):
    """Structured output for E7-review — holistic financial review."""
    insights: list[ReviewInsight] = Field(default_factory=list, description="Key insights from the analysis")
    recommendations: list[str] = Field(default_factory=list, description="Prioritized recommendations")
    score_adjustments: list[ScoreAdjustment] = Field(default_factory=list)
    narrative_sections: list[NarrativeSection] = Field(default_factory=list)
    overall_assessment: str = Field(..., description="Overall financial health assessment (2-3 paragraphs)")
    risk_level: str = Field(..., description="Overall risk level: low, moderate, high, critical")
    confidence: float = Field(..., ge=0.0, le=1.0)
