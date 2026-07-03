"""Logger JSON estruturado do pipeline (ADR-273) — espelho stdlib do ADR-110.

Campos emitidos casam com o ``MathomsJsonFormatter`` do backend
(``trace_id``/``workspace_id``/``pipeline_run_id``) para correlação
ponta-a-ponta sem tradução, + ``stage``/``event``/``duration_ms``
operacionais (condições do co-design sre-devops). Honra as mesmas env
vars do backend: ``MATHOMS_LOG_FORMAT`` (``json`` default, ``text`` dev)
e ``MATHOMS_LOG_LEVEL``.

Handler escreve em ``sys.__stderr__`` (stream original do processo): o
orchestrator redireciona ``sys.stdout``/``sys.stderr`` durante o stage
(um handler comum teria o log engolido pelo buffer de captura) e o CLI
``run-stage`` (ADR-150 A3.cli) reserva o stdout para o JSON puro do
``StageResult`` — log estruturado no stdout quebraria esse contrato.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any

from pipeline.observability.context import (
    get_run_id,
    get_stage,
    get_trace_id,
    get_workspace_id,
)
from pipeline.observability.redaction import (
    REDACTED_PLACEHOLDER,
    is_sensitive_key,
    redact,
)

_LOGGER_ROOT = "mathoms.pipeline"

#: Atributos padrão de ``LogRecord`` — o que sobrar veio de ``extra=``.
_STD_RECORD_ATTRS = frozenset(
    logging.LogRecord("x", logging.INFO, "x", 0, "x", None, None).__dict__
) | {"message", "asctime", "taskName"}


def _context_fields() -> dict[str, str]:
    """Campos de contexto do run presentes (nomes casam com o backend)."""
    fields = {
        "trace_id": get_trace_id(),
        "workspace_id": get_workspace_id(),
        "pipeline_run_id": get_run_id(),
        "stage": get_stage(),
    }
    return {key: value for key, value in fields.items() if value}


def _extra_fields(record: logging.LogRecord, payload: dict[str, Any]) -> dict[str, Any]:
    """Atributos vindos de ``extra=``, redigidos por chave (denylist única)."""
    extras: dict[str, Any] = {}
    for key, value in record.__dict__.items():
        if key in _STD_RECORD_ATTRS or key in payload:
            continue
        extras[key] = REDACTED_PLACEHOLDER if is_sensitive_key(key) else redact(value)
    return extras


class PipelineJsonFormatter(logging.Formatter):
    """JSON lines com timestamp ISO UTC + contexto do run + extra redacted."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": (
                datetime.fromtimestamp(record.created, tz=timezone.utc)
                .isoformat()
                .replace("+00:00", "Z")
            ),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        payload.update(_context_fields())
        payload.update(_extra_fields(record, payload))
        if record.exc_info and record.exc_info[0] is not None:
            payload["exc_type"] = record.exc_info[0].__name__
        return json.dumps(payload, ensure_ascii=False, default=str)


class _PipelineTextFormatter(logging.Formatter):
    """Texto plano para dev local (``MATHOMS_LOG_FORMAT=text``)."""

    def format(self, record: logging.LogRecord) -> str:
        base = super().format(record)
        stage = get_stage()
        return f"{base} [stage={stage}]" if stage else base


def _resolve_level() -> int:
    name = os.environ.get("MATHOMS_LOG_LEVEL", "INFO").upper()
    return getattr(logging, name, logging.INFO)


# A propagação segue ativa: no worker Celery quem formata é o handler do
# backend (MathomsJsonFormatter), que não lê os contextvars do pipeline —
# os atributos estampados viajam como extra e chegam ao JSON de qualquer
# formatter.
class _ContextStampFilter(logging.Filter):
    """Estampa o contexto do run como atributos do record (para propagação)."""

    _mathoms_pipeline_stamp = True

    def filter(self, record: logging.LogRecord) -> bool:
        for attr, value in _context_fields().items():
            if getattr(record, attr, None) is None:
                setattr(record, attr, value)
        return True


def _root_has_managed_handler() -> bool:
    return any(getattr(h, "_mathoms_managed", False) for h in logging.getLogger().handlers)


# Propagação fica ativa (caplog/pytest e coexistência com o root do backend
# dependem disso). Handler próprio só quando o processo não tem o handler
# gerenciado do backend (CLI standalone) — no worker, o record propaga ao
# handler do backend com o contexto estampado pelo filter.
def _ensure_handler() -> None:
    """Configura o logger raiz do pipeline uma vez (singleton idempotente ADR-111 §1.b)."""
    root = logging.getLogger(_LOGGER_ROOT)
    already_managed = any(getattr(h, "_mathoms_pipeline_managed", False) for h in root.handlers)
    if already_managed or _root_has_managed_handler():
        return
    handler = logging.StreamHandler(sys.__stderr__)
    handler._mathoms_pipeline_managed = True  # type: ignore[attr-defined]
    if os.environ.get("MATHOMS_LOG_FORMAT", "json").lower() == "text":
        handler.setFormatter(
            _PipelineTextFormatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
        )
    else:
        handler.setFormatter(PipelineJsonFormatter())
    root.addHandler(handler)
    root.setLevel(_resolve_level())


def get_logger(name: str) -> logging.Logger:
    """Logger sob ``mathoms.pipeline.*`` com contexto estampado e handler garantido."""
    _ensure_handler()
    if not name.startswith(_LOGGER_ROOT):
        name = f"{_LOGGER_ROOT}.{name}"
    logger = logging.getLogger(name)
    # Filter de logger não propaga a filhos — estampa por instância retornada.
    if not any(isinstance(f, _ContextStampFilter) for f in logger.filters):
        logger.addFilter(_ContextStampFilter())
    return logger


# Preserva o primeiro ERROR (a causa raiz costuma ser o primeiro evento, não
# o último sintoma — condição sre-devops), os últimos max_events e contadores
# por nível; as_summary() respeita o hard cap de bytes.
class StageLogTail(logging.Handler):
    """Tail bounded de WARNING/ERROR de um stage (ADR-273 §Retenção)."""

    def __init__(self, *, max_events: int = 50, max_bytes: int = 8192) -> None:
        super().__init__(level=logging.WARNING)
        self._max_events = max_events
        self._max_bytes = max_bytes
        self._first_error: dict[str, Any] | None = None
        self._events: list[dict[str, Any]] = []
        self._counters: dict[str, int] = {}

    def emit(self, record: logging.LogRecord) -> None:
        event = {"level": record.levelname, "message": record.getMessage()}
        self._counters[record.levelname] = self._counters.get(record.levelname, 0) + 1
        if record.levelno >= logging.ERROR and self._first_error is None:
            self._first_error = event
        self._events.append(event)
        if len(self._events) > self._max_events:
            self._events.pop(0)

    @property
    def first_error_message(self) -> str | None:
        return self._first_error["message"] if self._first_error else None

    def has_events(self) -> bool:
        return bool(self._counters)

    def as_summary(self) -> dict[str, Any]:
        """Dict JSON-ready ≤ ``max_bytes`` (derruba eventos antigos até caber)."""
        events = list(self._events)
        summary = self._build(events)
        while events and len(json.dumps(summary, ensure_ascii=False)) > self._max_bytes:
            events.pop(0)
            summary = self._build(events)
        return summary

    def _build(self, events: list[dict[str, Any]]) -> dict[str, Any]:
        summary: dict[str, Any] = {"counters": dict(self._counters), "events": events}
        if self._first_error and self._first_error not in events:
            summary["first_error"] = self._first_error
        return summary


__all__ = ["PipelineJsonFormatter", "StageLogTail", "get_logger"]
