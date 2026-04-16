"""Emit fine-grained pipeline progress when running inside the web worker (Celery).

CLI / tests: ``pipeline_run_id`` is unset → all calls are no-ops.
"""

from __future__ import annotations

from typing import Any


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
