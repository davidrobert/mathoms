"""Section summary output schema (v2.9 · ADR-144)."""
# Output tipado para SectionSummaryGenerator — prosa curta (1-2 frases)
# por seção. LLM nunca emite BRL formatado inline; referencia métrica
# via key_metric_ref e renderer formata com <MonetaryValue/> (ADR-090).

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class SectionSummaryOutput(BaseModel):
    """Estrutura de saída do LLM para uma seção do relatório."""

    summary_md: str = Field(
        ...,
        min_length=10,
        max_length=400,
        description=(
            "Prosa em português brasileiro, 1-2 frases, sem markdown além de "
            "ênfase leve. Não formate valores monetários inline — use "
            "key_metric_ref para apontar a métrica."
        ),
    )
    tone: Literal["neutral", "positive", "warning"] = Field(
        "neutral",
        description="Tom narrativo da seção; orienta o renderer (cor de borda, ícone).",
    )
    key_metric_ref: Optional[str] = Field(
        None,
        max_length=80,
        description=(
            "Id da métrica principal referenciada (ex.: 'patrimonio.liquido'). "
            "Renderer pode usar para destacar valor via <MonetaryValue/>."
        ),
    )
