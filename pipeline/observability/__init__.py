"""Observabilidade do pipeline (ADR-273) — contexto, logger e redação, zero deps de framework."""

from pipeline.observability.context import (
    BindTokens,
    bind,
    get_run_id,
    get_stage,
    get_trace_id,
    get_workspace_id,
    reset,
)
from pipeline.observability.logger import (
    PipelineJsonFormatter,
    StageLogTail,
    get_logger,
)
from pipeline.observability.redaction import (
    REDACTED_PLACEHOLDER,
    SENSITIVE_FIELD_SUBSTRINGS,
    is_sensitive_key,
    redact,
)

__all__ = [
    "BindTokens",
    "PipelineJsonFormatter",
    "REDACTED_PLACEHOLDER",
    "SENSITIVE_FIELD_SUBSTRINGS",
    "StageLogTail",
    "bind",
    "get_logger",
    "get_run_id",
    "get_stage",
    "get_trace_id",
    "get_workspace_id",
    "is_sensitive_key",
    "redact",
    "reset",
]
