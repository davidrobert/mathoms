"""Emit fine-grained pipeline progress when running inside the web worker (Celery).

CLI / tests: ``pipeline_run_id`` is unset → all calls are no-ops.
"""

from __future__ import annotations

import os
from typing import Any, Literal

# ADR-119: fases válidas do contrato LiveStep. Espelha `LiveStepPhase` em
# backend/app/services/pipeline/events.py — duplicada aqui para manter pipeline/
# sem import obrigatório de backend/ (boundary check).
LiveStepPhase = Literal["preparing", "awaiting_llm", "validating", "persisting", "finalizing"]

# A37.l12 (CTO-06): cadência do heartbeat in-stage — DB write a cada N docs.
_HEARTBEAT_EVERY_N_DOCS_ENV = "MATHOMS_HEARTBEAT_EVERY_N_DOCS"
# Cadência default 10: com watchdog de 15 min, qualquer stage que processe ≥1
# doc/90s renova a tempo; batida por-doc multiplicava contenção de lock no dev.
_DEFAULT_HEARTBEAT_EVERY_N_DOCS = 10


def emit_stage_activity(
    run_id: str | None,
    stage: str,
    *,
    file: str | None = None,
    message: str | None = None,
    **extra: Any,
) -> None:
    """Notify subscribers (WebSocket) about work inside a stage (e.g. current file)."""
    if not run_id:
        return
    try:
        from backend.app.services.pipeline.events import publish_stage_activity

        publish_stage_activity(
            run_id,
            stage,
            file=file,
            message=message,
            extra=extra or None,
        )
    except Exception:
        pass


def emit_item_progress(
    run_id: str | None,
    stage: str,
    *,
    current_item: str | None,
    items_done: int,
    items_total: int,
    phase: LiveStepPhase,
    estimated_duration_ms: int | None = None,
) -> None:
    """Emit LiveStep item progress (ADR-119) — throttled no backend a 250ms.

    Chame antes de iniciar cada item (``phase="preparing"``) e ao entrar em
    sub-fases longas (``awaiting_llm``, ``validating``, ``persisting``). O
    último item da stage usa ``phase="finalizing"`` (nunca throttled).
    """
    if not run_id:
        return
    try:
        from backend.app.services.pipeline.events import publish_item_progress

        publish_item_progress(
            run_id,
            stage,
            current_item=current_item,
            items_done=items_done,
            items_total=items_total,
            phase=phase,
            estimated_duration_ms=estimated_duration_ms,
        )
    except Exception:
        pass
    _record_heartbeat_every_n_docs(run_id, items_done)


def _heartbeat_every_n_docs() -> int:
    raw = os.environ.get(_HEARTBEAT_EVERY_N_DOCS_ENV)
    try:
        value = int(raw) if raw else _DEFAULT_HEARTBEAT_EVERY_N_DOCS
    except ValueError:
        return _DEFAULT_HEARTBEAT_EVERY_N_DOCS
    return value if value >= 1 else _DEFAULT_HEARTBEAT_EVERY_N_DOCS


def _record_heartbeat_every_n_docs(run_id: str, items_done: int) -> None:
    """Heartbeat in-stage (A37.l12 · CTO-06) — DB write CAS a cada N docs, inline no loop de documentos: sem thread/timer no worker (ADR-111) e sem estado in-memory (cadência deriva de ``items_done`` passado pelo stage)."""
    if items_done % _heartbeat_every_n_docs() != 0:
        return
    try:
        from backend.app.services.pipeline.heartbeat import record_in_stage_heartbeat

        record_in_stage_heartbeat(run_id)
    except Exception:
        pass
