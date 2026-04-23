"""WebSocket router fino — real-time pipeline progress (A6e.4 · ADR-101 R15/R16).

Subscribes to Redis Pub/Sub channel ``pipeline:{run_id}`` e encaminha eventos.
Degrada graciosamente se Redis indisponível.
"""

from __future__ import annotations

from fastapi import APIRouter, Query, WebSocket

from backend.app.application.realtime import (
    stream_pipeline_progress,
    verify_ws_token,
)

router = APIRouter(tags=["websocket"])


@router.websocket("/pipeline/runs/{run_id}/ws")
async def ws_pipeline_progress(
    websocket: WebSocket,
    run_id: str,
    token: str = Query(default=""),
) -> None:
    """Live pipeline progress. Auth via ``?token=<jwt>``."""
    user_id = verify_ws_token(token)
    if not user_id:
        await websocket.close(code=4001, reason="Invalid or missing token")
        return
    await websocket.accept()
    await stream_pipeline_progress(websocket, run_id)
