"""Emit fine-grained pipeline progress when running inside the web worker (Celery).

CLI / tests: ``pipeline_run_id`` is unset → all calls are no-ops.
"""

from __future__ import annotations

from typing import Any, Literal

# ADR-119: fases válidas do contrato LiveStep. Espelha `LiveStepPhase` em
# backend/app/services/events.py — duplicada aqui para manter pipeline/
# sem import obrigatório de backend/ (boundary check).
LiveStepPhase = Literal["preparing", "awaiting_llm", "validating", "persisting", "finalizing"]


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
        from backend.app.services.events import publish_stage_activity

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
        from backend.app.services.events import publish_item_progress

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
