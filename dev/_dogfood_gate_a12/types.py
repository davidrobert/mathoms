"""Dataclasses de resultado do gate."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RuleResult:
    """Resultado de 1 regra testada (preview + create)."""

    keyword: str
    target_category: str
    preview_matches_total: int = 0
    preview_in_closed_months: int = 0
    preview_with_manual_override: int = 0
    preview_blocked_internal_transfers: int = 0
    preview_warnings: list[str] = field(default_factory=list)
    preview_requires_confirmation: bool = False
    create_status: str = "not_attempted"
    create_applied_count: int = 0
    create_estimated_matches: int = 0
    create_async_path: bool = False
    rule_id: str | None = None
    error_message: str | None = None


@dataclass
class GateInvariant:
    code: str
    description: str
    status: str  # PASS | FAIL | WARN | N/A
    detail: str


@dataclass
class GateReport:
    verdict: str = "UNKNOWN"
    workspace_id: str = ""
    total_transactions: int = 0
    closed_months: list[str] = field(default_factory=list)
    manual_overrides_seeded: int = 0
    rules: list[RuleResult] = field(default_factory=list)
    invariants: list[GateInvariant] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)


__all__ = ["GateInvariant", "GateReport", "RuleResult"]
