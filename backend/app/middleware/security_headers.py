"""Security headers HTTP em toda resposta do backend (W2-T02 · ADR-232)."""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from backend.app.core.config import settings

HSTS_VALUE = "max-age=31536000; includeSubDomains"
X_FRAME_OPTIONS_VALUE = "DENY"
X_CONTENT_TYPE_OPTIONS_VALUE = "nosniff"
REFERRER_POLICY_VALUE = "strict-origin-when-cross-origin"

PERMISSIONS_POLICY_VALUE = (
    "accelerometer=(), camera=(), geolocation=(), gyroscope=(), "
    "magnetometer=(), microphone=(), payment=(), usb=()"
)


def _build_csp_report_only(api_prefix: str) -> str:
    report_uri = f"{api_prefix}/csp-report"
    return (
        "default-src 'self'; "
        "script-src 'self' https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "img-src 'self' data: blob: https://fastapi.tiangolo.com; "
        "font-src 'self' data:; "
        "connect-src 'self'; "
        "worker-src 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'; "
        "object-src 'none'; "
        f"report-uri {report_uri}"
    )


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Emite headers de segurança HTTP em toda resposta."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)
        self._csp_report_only = _build_csp_report_only(settings.API_PREFIX)

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        headers = response.headers
        headers.setdefault("Strict-Transport-Security", HSTS_VALUE)
        headers.setdefault("X-Frame-Options", X_FRAME_OPTIONS_VALUE)
        headers.setdefault("X-Content-Type-Options", X_CONTENT_TYPE_OPTIONS_VALUE)
        headers.setdefault("Referrer-Policy", REFERRER_POLICY_VALUE)
        headers.setdefault("Permissions-Policy", PERMISSIONS_POLICY_VALUE)
        headers.setdefault("Content-Security-Policy-Report-Only", self._csp_report_only)
        return response
