"""WebSocket endpoint — forwards Redis pub/sub events to connected clients.

Subscribes to `pipeline:{run_id}` and pushes JSON frames to the WS peer
until the client disconnects or a terminal event arrives.
"""

from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(prefix="/api/v1/pipeline/events", tags=["events"])

logger = logging.getLogger("mathoms.pipeline_service.ws")

TERMINAL_EVENTS = frozenset({"run_completed", "run_failed", "run_cancelled"})


@router.websocket("/{run_id}")
async def stream_events(ws: WebSocket, run_id: str) -> None:
    """Stream events for a given run until terminal or disconnect."""
    await ws.accept()
    pubsub = _subscribe(run_id)
    if pubsub is None:
        await ws.send_json({"event": "error", "error": "redis_unavailable"})
        await ws.close(code=1011)
        return

    try:
        while True:
            msg = pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if msg is None:
                await asyncio.sleep(0.1)
                continue
            payload = _decode(msg)
            if payload is None:
                continue
            await ws.send_json(payload)
            if payload.get("event") in TERMINAL_EVENTS:
                await ws.close()
                return
    except WebSocketDisconnect:
        return
    finally:
        try:
            pubsub.close()
        except Exception:
            pass


def _subscribe(run_id: str):
    from app.services.event_publisher import _get_client

    client = _get_client()
    if client is None:
        return None
    pubsub = client.pubsub()
    pubsub.subscribe(f"pipeline:{run_id}")
    return pubsub


def _decode(msg: dict) -> dict | None:
    data = msg.get("data")
    if not data:
        return None
    try:
        return json.loads(data)
    except json.JSONDecodeError:
        logger.warning("ws_decode_failed data=%r", data)
        return None
