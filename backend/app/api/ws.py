"""WebSocket endpoint for real-time pipeline progress.

Subscribes to Redis Pub/Sub channel `pipeline:{run_id}` and forwards events.
Falls back gracefully if Redis is unavailable.
"""

from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from jose import JWTError, jwt

from backend.app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])


def _verify_ws_token(token: str) -> str | None:
    """Validate JWT from WebSocket handshake. Returns user_id or None."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str | None = payload.get("sub")
        return user_id
    except JWTError:
        return None


@router.websocket("/pipeline/runs/{run_id}/ws")
async def ws_pipeline_progress(
    websocket: WebSocket,
    run_id: str,
    token: str = Query(default=""),
):
    """WebSocket endpoint for live pipeline progress.

    Auth: JWT passed as query param `?token=<jwt>`.
    Subscribes to Redis Pub/Sub `pipeline:{run_id}` and forwards JSON events.
    Sends heartbeat every 15s to keep connection alive.
    """
    user_id = _verify_ws_token(token)
    if not user_id:
        await websocket.close(code=4001, reason="Invalid or missing token")
        return

    await websocket.accept()

    redis_sub = None
    try:
        import redis.asyncio as aioredis

        redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        redis_sub = redis_client.pubsub()
        await redis_sub.subscribe(f"pipeline:{run_id}")
    except Exception as exc:
        logger.warning("Redis unavailable for WS subscription: %s", exc)
        await websocket.send_json(
            {
                "event": "error",
                "detail": "Real-time updates unavailable. Use polling.",
            }
        )
        await websocket.close(code=1011, reason="Redis unavailable")
        return

    try:
        while True:
            message = await asyncio.wait_for(
                redis_sub.get_message(ignore_subscribe_messages=True, timeout=15.0),
                timeout=20.0,
            )

            if message and message["type"] == "message":
                try:
                    data = json.loads(message["data"])
                    await websocket.send_json(data)

                    if data.get("event") in ("run_completed", "run_failed", "run_cancelled"):
                        await websocket.close(code=1000, reason="Run finished")
                        return
                except (json.JSONDecodeError, Exception) as exc:
                    logger.warning("Error forwarding WS message: %s", exc)
            else:
                await websocket.send_json({"event": "heartbeat"})

    except WebSocketDisconnect:
        logger.debug("WS client disconnected for run %s", run_id)
    except asyncio.TimeoutError:
        await websocket.send_json({"event": "heartbeat"})
    except Exception as exc:
        logger.warning("WS error for run %s: %s", run_id, exc)
    finally:
        if redis_sub:
            try:
                await redis_sub.unsubscribe(f"pipeline:{run_id}")
                await redis_sub.close()
                await redis_client.close()
            except Exception:
                pass
