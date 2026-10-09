"""Section summary output schema (v2.9 · ADR-144)."""
# Output tipado para SectionSummaryGenerator — prosa curta (1-2 frases)
# por seção, texto puro (o renderer imprime literal). Só `summary_md`:
# `tone` e `key_metric_ref` saíram no prompt 2.0.0 por não terem leitor
# (ADR-144 §Emenda 2026-10-09). No Mode.TOOLS do Instructor, docstring e
# `description` vão ao modelo — mudá-los muda o prompt; a chave de cache
# cobre o schema por fingerprint.

from __future__ import annotations

from pydantic import BaseModel, Field


class SectionSummaryOutput(BaseModel):
    """Estrutura de saída do LLM para uma seção do relatório."""

    summary_md: str = Field(
        ...,
        min_length=10,
        max_length=400,
        description=(
            "Prosa em português brasileiro, 1-2 frases, texto puro sem markdown. "
            "Sem valores monetários: o leitor já vê os KPIs no cabeçalho da seção."
        ),
    )
