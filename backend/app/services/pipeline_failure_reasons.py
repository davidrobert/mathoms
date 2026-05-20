"""Vocabulário aberto de ``PipelineRun.failure_reason`` (ADR-172, W2-T04)."""

from __future__ import annotations

#: Beat task ``fin.detect_stuck_runs`` flagou run com heartbeat estale.
HEARTBEAT_TIMEOUT = "heartbeat_timeout"

ALL_REASONS: frozenset[str] = frozenset({HEARTBEAT_TIMEOUT})
