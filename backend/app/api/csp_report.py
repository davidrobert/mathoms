"""Endpoint ingestor anônimo de violations CSP (W2-T02 · ADR-232 §D2)."""

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, Request, status
from fastapi.responses import Response

logger = logging.getLogger("mathoms.security.csp")

router = APIRouter(tags=["security"])

MAX_CSP_REPORT_BYTES = 8192


def _declared_oversized(content_length: str | None) -> bool:
    if content_length is None:
        return False
    try:
        return int(content_length) > MAX_CSP_REPORT_BYTES
    except ValueError:
        return True


def _oversized(request: Request, body: bytes) -> bool:
    if _declared_oversized(request.headers.get("content-length")):
        return True
    return len(body) > MAX_CSP_REPORT_BYTES


def _try_parse(body: bytes) -> tuple[bool, Any]:
    try:
        return True, json.loads(body or b"null")
    except (ValueError, TypeError):
        return False, None


@router.post(
    "/csp-report",
    status_code=status.HTTP_204_NO_CONTENT,
    include_in_schema=False,
)
async def report_csp_violation(request: Request) -> Response:
    body = await request.body()
    if _oversized(request, body):
        return Response(status_code=413)
    parsed, payload = _try_parse(body)
    if not parsed:
        logger.warning(
            "csp.violation.unparseable",
            extra={
                "raw_bytes": len(body),
                "content_type": request.headers.get("content-type", ""),
            },
        )
        return Response(status_code=204)
    logger.warning(
        "csp.violation",
        extra={"csp_payload": payload, "user_agent": request.headers.get("user-agent", "")},
    )
    return Response(status_code=204)
