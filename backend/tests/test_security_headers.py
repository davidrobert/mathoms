"""Security headers + CORS strict — W2-T02 · ADR-232."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from starlette.testclient import TestClient

from backend.app.core.config import settings
from backend.app.middleware.security_headers import (
    HSTS_VALUE,
    PERMISSIONS_POLICY_VALUE,
    REFERRER_POLICY_VALUE,
    X_CONTENT_TYPE_OPTIONS_VALUE,
    X_FRAME_OPTIONS_VALUE,
    SecurityHeadersMiddleware,
    _build_csp_report_only,
)

_ALLOWED_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
_ALLOWED_HEADERS = [
    "Authorization",
    "Content-Type",
    "X-Trace-Id",
    "X-Workspace-Id",
    "Accept",
    "Accept-Language",
    "If-None-Match",
    "If-Modified-Since",
]


def _attach_cors(app: FastAPI) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=_ALLOWED_METHODS,
        allow_headers=_ALLOWED_HEADERS,
        expose_headers=["X-Trace-Id"],
        max_age=600,
    )


@pytest.fixture
def app() -> FastAPI:
    inner = FastAPI()
    inner.add_middleware(SecurityHeadersMiddleware)
    _attach_cors(inner)

    @inner.get("/ping")
    def ping():
        return {"ok": True}

    @inner.get("/server-error")
    def server_error():
        return JSONResponse({"detail": "boom"}, status_code=500)

    return inner


def test_security_headers_present_on_2xx(app: FastAPI):
    client = TestClient(app)
    resp = client.get("/ping")
    assert resp.status_code == 200
    assert resp.headers["strict-transport-security"] == HSTS_VALUE
    assert resp.headers["x-frame-options"] == X_FRAME_OPTIONS_VALUE
    assert resp.headers["x-content-type-options"] == X_CONTENT_TYPE_OPTIONS_VALUE
    assert resp.headers["referrer-policy"] == REFERRER_POLICY_VALUE
    assert resp.headers["permissions-policy"] == PERMISSIONS_POLICY_VALUE
    csp = resp.headers["content-security-policy-report-only"]
    assert "default-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp
    assert "object-src 'none'" in csp
    assert "report-uri" in csp


def test_security_headers_present_on_500_response(app: FastAPI):
    client = TestClient(app)
    resp = client.get("/server-error")
    assert resp.status_code == 500
    assert resp.headers.get("strict-transport-security") == HSTS_VALUE
    assert resp.headers.get("x-frame-options") == X_FRAME_OPTIONS_VALUE


def test_security_headers_present_on_404(app: FastAPI):
    client = TestClient(app)
    resp = client.get("/does-not-exist")
    assert resp.status_code == 404
    assert resp.headers.get("strict-transport-security") == HSTS_VALUE
    assert resp.headers.get("content-security-policy-report-only", "").startswith(
        "default-src 'self'"
    )


def test_csp_policy_lists_jsdelivr_for_swagger_ui():
    csp = _build_csp_report_only(settings.API_PREFIX)
    assert "https://cdn.jsdelivr.net" in csp
    assert "report-uri " in csp


def test_csp_report_uri_uses_api_prefix():
    csp = _build_csp_report_only("/api/v1")
    assert "report-uri /api/v1/csp-report" in csp


def test_cors_preflight_allowed_origin_accepts_listed_method(app: FastAPI):
    client = TestClient(app)
    resp = client.options(
        "/ping",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Authorization,Content-Type",
        },
    )
    assert resp.status_code == 200
    assert resp.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert "POST" in resp.headers["access-control-allow-methods"]
    assert "Authorization" in resp.headers["access-control-allow-headers"]


def test_cors_preflight_rejects_disallowed_origin(app: FastAPI):
    client = TestClient(app)
    resp = client.options(
        "/ping",
        headers={
            "Origin": "https://attacker.example.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert "access-control-allow-origin" not in resp.headers


def test_cors_preflight_rejects_disallowed_method(app: FastAPI):
    client = TestClient(app)
    resp = client.options(
        "/ping",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "TRACE",
        },
    )
    assert resp.status_code == 400


def test_cors_preflight_rejects_disallowed_header(app: FastAPI):
    client = TestClient(app)
    resp = client.options(
        "/ping",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "X-Custom-Forbidden",
        },
    )
    assert resp.status_code == 400


def test_cors_no_wildcard_in_allow_origin(app: FastAPI):
    client = TestClient(app)
    resp = client.get("/ping", headers={"Origin": "http://localhost:3000"})
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:3000"
    assert resp.headers.get("access-control-allow-origin") != "*"


def test_existing_header_not_overridden():
    inner = FastAPI()
    inner.add_middleware(SecurityHeadersMiddleware)

    @inner.get("/strict-frame")
    def strict_frame():
        return JSONResponse({"ok": True}, headers={"X-Frame-Options": "SAMEORIGIN"})

    client = TestClient(inner)
    resp = client.get("/strict-frame")
    assert resp.headers["x-frame-options"] == "SAMEORIGIN"
    assert resp.headers["strict-transport-security"] == HSTS_VALUE
