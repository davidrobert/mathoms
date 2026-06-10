"""Schemas do loop de debug de lineage (ADR-281 · A25.l4 F7) — structured output Instructor: cada passo do loop ou pede 1 tool (expand_node/trace_source) ou entrega a localização final; parse-fail 2× = miss, nunca crash."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator


class LocalizationResult(BaseModel):
    """Localização final: node_id ``(stage, artifact_key, field)`` do nó-origem do bug."""

    stage: str = Field(..., min_length=1, max_length=40)
    artifact_key: str = Field(..., min_length=1, max_length=120)
    field: str = Field(..., min_length=1, max_length=200)
    confidence: Literal["alta", "media", "baixa"]
    reasoning_short: str = Field(..., min_length=1, max_length=400)

    def node_id(self) -> tuple[str, str, str]:
        return (self.stage, self.artifact_key, self.field)


class LineageDebugStep(BaseModel):
    """Um passo do loop: tool request OU localização — nunca os dois vazios."""

    action: Literal["expand_node", "trace_source", "localize"]
    stage: Optional[str] = Field(None, max_length=40)
    artifact_key: Optional[str] = Field(None, max_length=120)
    field: Optional[str] = Field(None, max_length=200)
    localization: Optional[LocalizationResult] = None

    @model_validator(mode="after")
    def _action_payload_consistent(self) -> "LineageDebugStep":
        if self.action == "localize" and self.localization is None:
            raise ValueError("action='localize' exige localization preenchida")
        if self.action != "localize" and not self.field:
            raise ValueError(f"action={self.action!r} exige field do nó/campo alvo")
        return self
