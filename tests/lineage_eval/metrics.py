"""Métricas do eval de localização (ADR-281 · A25.l4 F7): localization_accuracy@node (KR1 ≥85%), tool_iterations_p95 (KR3 ≤6), tokens_to_localization, custo agregado e trials_agreement (proxy de estabilidade enquanto litellm_client não expõe seed)."""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from dataclasses import dataclass


@dataclass(frozen=True)
class TrialRecord:
    case_id: str
    family: str
    sealed: bool
    predicted: tuple[str, str, str] | None
    target: tuple[str, str, str]
    tool_iterations: int
    llm_calls: int
    tokens_in: int
    tokens_out: int
    usd_spent: float  # rate USD estimado de API LLM, não money de domínio (ADR-090)
    miss_reason: str | None

    @property
    def hit(self) -> bool:
        return self.predicted == self.target

    def to_dict(self) -> dict:
        return {
            "case_id": self.case_id,
            "family": self.family,
            "sealed": self.sealed,
            "hit": self.hit,
            "predicted": list(self.predicted) if self.predicted else None,
            "target": list(self.target),
            "tool_iterations": self.tool_iterations,
            "llm_calls": self.llm_calls,
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "usd_spent": round(self.usd_spent, 6),
            "miss_reason": self.miss_reason,
        }


def percentile_95(values: list[int]) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    index = max(0, math.ceil(0.95 * len(ordered)) - 1)
    return ordered[index]


def _accuracy(records: list[TrialRecord]) -> float:
    return sum(r.hit for r in records) / len(records) if records else 0.0


def _by_family(records: list[TrialRecord]) -> dict[str, float]:
    grouped: dict[str, list[TrialRecord]] = defaultdict(list)
    for record in records:
        grouped[record.family].append(record)
    return {family: round(_accuracy(group), 4) for family, group in sorted(grouped.items())}


def _trials_agreement(records: list[TrialRecord]) -> float:
    """Média por caso da fração de trials que concordam com a predição modal."""
    grouped: dict[str, list[tuple[str, str, str] | None]] = defaultdict(list)
    for record in records:
        grouped[record.case_id].append(record.predicted)
    agreements = [
        Counter(preds).most_common(1)[0][1] / len(preds) for preds in grouped.values() if preds
    ]
    return sum(agreements) / len(agreements) if agreements else 0.0


def aggregate_metrics(records: list[TrialRecord]) -> dict:
    tokens = [r.tokens_in + r.tokens_out for r in records]
    return {
        "trials": len(records),
        "localization_accuracy_at_node": round(_accuracy(records), 4),
        "accuracy_by_family": _by_family(records),
        "tool_iterations_p95": percentile_95([r.tool_iterations for r in records]),
        "tokens_to_localization_mean": round(sum(tokens) / len(tokens), 1) if tokens else 0.0,
        "total_usd_spent": round(sum(r.usd_spent for r in records), 6),
        "trials_agreement_mean": round(_trials_agreement(records), 4),
    }
