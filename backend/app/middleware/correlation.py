"""Correlation ID middleware — request-scoped trace propagation (A6f.3 · ADR-110).

Pulls `X-Trace-Id` header (or generates a new UUID v4) and exposes it via a
`contextvars.ContextVar` so any log emitted during the request picks it up
automatically through `MathomsJsonFormatter`.

Also tracks `workspace_id`, `user_id`, and `pipeline_run_id` set by
downstream dependencies (e.g. tenancy guard, pipeline task).
"""

from __future__ import annotations

import uuid
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

TRACE_ID_HEADER = "X-Trace-Id"

_trace_id: ContextVar[str | None] = ContextVar("mathoms_trace_id", default=None)
_workspace_id: ContextVar[str | None] = ContextVar("mathoms_workspace_id", default=None)
_user_id: ContextVar[str | None] = ContextVar("mathoms_user_id", default=None)
_pipeline_run_id: ContextVar[str | None] = ContextVar("mathoms_pipeline_run_id", default=None)


def get_trace_id() -> str | None:
    return _trace_id.get()


def set_trace_id(value: str | None) -> object:
    return _trace_id.set(value)


def get_workspace_id() -> str | None:
    return _workspace_id.get()


def set_workspace_id(value: str | None) -> object:
    return _workspace_id.set(value)


def get_user_id() -> str | None:
    return _user_id.get()


def set_user_id(value: str | None) -> object:
    return _user_id.set(value)


def get_pipeline_run_id() -> str | None:
    return _pipeline_run_id.get()


def set_pipeline_run_id(value: str | None) -> object:
    return _pipeline_run_id.set(value)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Sets/propagates trace_id contextvar for the duration of each request."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next) -> Response:
        incoming = request.headers.get(TRACE_ID_HEADER)
        trace_id = incoming if incoming else str(uuid.uuid4())

        trace_token = _trace_id.set(trace_id)
        try:
            response = await call_next(request)
        finally:
            _trace_id.reset(trace_token)

        response.headers[TRACE_ID_HEADER] = trace_id
        return response
