"""Structured JSON logging setup (A6f.3 · ADR-110).

Single source of logging configuration for the API process and Celery worker.
Emits JSON lines to stdout with ISO 8601 UTC timestamps, severity, logger
name, message, plus correlation/trace context pulled from contextvars.

Format is controlled by `MATHOMS_LOG_FORMAT` (`json` default, `text` for
local debugging). Level by `MATHOMS_LOG_LEVEL` (default `INFO`).
"""

from __future__ import annotations

import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any

from pythonjsonlogger.json import JsonFormatter

from backend.app.middleware.correlation import (
    get_pipeline_run_id,
    get_trace_id,
    get_user_id,
    get_workspace_id,
)

# ADR-273: denylist canônica movida para pipeline/observability/redaction.py
# (fonte única backend↔pipeline; duplicar causaria drift). Re-export preserva
# os nomes históricos deste módulo para todos os consumidores existentes.
from pipeline.observability.redaction import (
    REDACTED_PLACEHOLDER,
    SENSITIVE_FIELD_SUBSTRINGS,
)
from pipeline.observability.redaction import (
    is_sensitive_key as _is_sensitive_key,
)
from pipeline.observability.redaction import (
    redact as _redact,
)

__all__ = [
    "MathomsJsonFormatter",
    "REDACTED_PLACEHOLDER",
    "SENSITIVE_FIELD_SUBSTRINGS",
    "get_logger",
    "setup_logging",
]


class MathomsJsonFormatter(JsonFormatter):
    """JSON formatter with ISO 8601 UTC timestamps and correlation context."""

    def add_fields(
        self,
        log_record: dict[str, Any],
        record: logging.LogRecord,
        message_dict: dict[str, Any],
    ) -> None:
        super().add_fields(log_record, record, message_dict)

        log_record["timestamp"] = (
            datetime.fromtimestamp(record.created, tz=timezone.utc)
            .isoformat()
            .replace("+00:00", "Z")
        )
        log_record["level"] = record.levelname
        log_record["logger"] = record.name
        log_record["message"] = record.getMessage()

        trace_id = get_trace_id()
        if trace_id:
            log_record["trace_id"] = trace_id
        workspace_id = get_workspace_id()
        if workspace_id:
            log_record["workspace_id"] = workspace_id
        user_id = get_user_id()
        if user_id:
            log_record["user_id"] = user_id
        pipeline_run_id = get_pipeline_run_id()
        if pipeline_run_id:
            log_record["pipeline_run_id"] = pipeline_run_id

        otel_trace_id = getattr(record, "otelTraceID", None)
        if otel_trace_id and otel_trace_id != "0":
            log_record["otel_trace_id"] = otel_trace_id
        otel_span_id = getattr(record, "otelSpanID", None)
        if otel_span_id and otel_span_id != "0":
            log_record["otel_span_id"] = otel_span_id

        log_record.pop("color_message", None)

        for key in list(log_record.keys()):
            if _is_sensitive_key(key):
                log_record[key] = REDACTED_PLACEHOLDER
            else:
                log_record[key] = _redact(log_record[key])


class _TextFormatter(logging.Formatter):
    """Plain text formatter for local dev — includes trace_id when present."""

    def format(self, record: logging.LogRecord) -> str:
        base = super().format(record)
        trace_id = get_trace_id()
        if trace_id:
            return f"{base} [trace={trace_id[:8]}]"
        return base


def _resolve_log_level() -> int:
    name = os.environ.get("MATHOMS_LOG_LEVEL", "INFO").upper()
    return getattr(logging, name, logging.INFO)


def _resolve_log_format() -> str:
    return os.environ.get("MATHOMS_LOG_FORMAT", "json").lower()


def setup_logging() -> None:
    """Configure root logger with JSON (or text) handler on stdout. Idempotent."""
    root = logging.getLogger()
    for h in list(root.handlers):
        if getattr(h, "_mathoms_managed", False):
            root.removeHandler(h)

    handler = logging.StreamHandler(sys.stdout)
    handler._mathoms_managed = True  # type: ignore[attr-defined]

    if _resolve_log_format() == "text":
        handler.setFormatter(_TextFormatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    else:
        handler.setFormatter(MathomsJsonFormatter())

    root.addHandler(handler)
    root.setLevel(_resolve_log_level())

    for noisy in ("uvicorn.access", "uvicorn.error", "uvicorn"):
        logging.getLogger(noisy).handlers = []
        logging.getLogger(noisy).propagate = True

    logging.getLogger("mathoms").setLevel(_resolve_log_level())


def get_logger(name: str) -> logging.Logger:
    """Return a logger under the `mathoms.` namespace."""
    if not name.startswith("mathoms."):
        name = f"mathoms.{name}"
    return logging.getLogger(name)
