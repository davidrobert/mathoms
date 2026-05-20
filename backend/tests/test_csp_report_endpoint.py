"""CSP report ingest endpoint — W2-T02 · ADR-232 §D2."""

from __future__ import annotations

import json

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from backend.app.api.csp_report import MAX_CSP_REPORT_BYTES, router


@pytest.fixture
def app() -> FastAPI:
    inner = FastAPI()
    inner.include_router(router, prefix="/api/v1")
    return inner


def test_csp_report_accepts_small_payload(app: FastAPI):
    client = TestClient(app)
    payload = {
        "csp-report": {
            "document-uri": "https://app.mathoms.ai/reports/abc",
            "violated-directive": "script-src",
            "blocked-uri": "https://evil.example.com/x.js",
        }
    }
    resp = client.post("/api/v1/csp-report", json=payload)
    assert resp.status_code == 204
    assert resp.content == b""


def test_csp_report_accepts_empty_body(app: FastAPI):
    client = TestClient(app)
    resp = client.post("/api/v1/csp-report", content=b"")
    assert resp.status_code == 204


def test_csp_report_rejects_oversized_via_content_length(app: FastAPI):
    client = TestClient(app)
    payload = json.dumps({"x": "y" * (MAX_CSP_REPORT_BYTES + 100)}).encode()
    assert len(payload) > MAX_CSP_REPORT_BYTES
    resp = client.post(
        "/api/v1/csp-report",
        content=payload,
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 413


def test_csp_report_tolerates_invalid_json(app: FastAPI):
    client = TestClient(app)
    resp = client.post(
        "/api/v1/csp-report",
        content=b"{not valid json",
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 204


def test_csp_report_not_in_openapi_schema(app: FastAPI):
    client = TestClient(app)
    spec = client.get("/openapi.json").json()
    assert "/api/v1/csp-report" not in spec.get("paths", {})
