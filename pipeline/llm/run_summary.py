"""``LLMRunSummary`` — agregado de uso de tokens/custo de um run inteiro."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pipeline.llm.litellm_client import LLMCallResult


@dataclass
class LLMRunSummary:
    """Aggregated token usage for an entire pipeline run."""

    calls: "list[LLMCallResult]" = field(default_factory=list)

    @property
    def total_tokens_in(self) -> int:
        return sum(c.tokens_in for c in self.calls)

    @property
    def total_tokens_out(self) -> int:
        return sum(c.tokens_out for c in self.calls)

    @property
    def total_cost_usd(self) -> float:
        return sum(c.cost_estimate_usd for c in self.calls)

    @property
    def total_duration_ms(self) -> int:
        return sum(c.duration_ms for c in self.calls)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_calls": len(self.calls),
            "total_tokens_in": self.total_tokens_in,
            "total_tokens_out": self.total_tokens_out,
            "total_cost_estimate_usd": round(self.total_cost_usd, 6),
            "total_duration_ms": self.total_duration_ms,
            "calls": [
                {
                    "provider": c.provider,
                    "model": c.model,
                    "tokens_in": c.tokens_in,
                    "tokens_out": c.tokens_out,
                    "cost_usd": round(c.cost_estimate_usd, 6),
                    "duration_ms": c.duration_ms,
                    "retries": c.retries_used,
                }
                for c in self.calls
            ],
        }
