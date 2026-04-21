"""Smoke — /health and OpenAPI advertising the three routes."""

from __future__ import annotations


def test_health_returns_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["service"] == "pipeline-service"
    assert body["version"]


def test_openapi_advertises_routes(client):
    r = client.get("/openapi.json")
    assert r.status_code == 200
    paths = r.json()["paths"]
    assert "/api/v1/pipeline/runs" in paths
    assert "/api/v1/pipeline/stages/{stage}/execute" in paths
