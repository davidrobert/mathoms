"""Use cases real-time (WebSocket) — A6e.4 · ADR-101 R15.

Pump loops Redis Pub/Sub → WebSocket + auth JWT do handshake. Routers
apenas fazem o accept do socket e delegam o ciclo de vida para cá.
"""

from backend.app.application.realtime.pipeline_progress import (
    stream_pipeline_progress,
    verify_ws_token,
)

__all__ = ["stream_pipeline_progress", "verify_ws_token"]
