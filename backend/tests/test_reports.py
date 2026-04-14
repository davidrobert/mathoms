"""Tests for report endpoints — list, get, html."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_reports_empty(auth_client: AsyncClient):
    resp = await auth_client.get("/api/reports")
    assert resp.status_code == 200
    data = resp.json()
    assert data["reports"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_list_reports_unauthorized(client: AsyncClient):
    resp = await client.get("/api/reports")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_get_report_not_found(auth_client: AsyncClient):
    resp = await auth_client.get("/api/reports/nonexistent-id")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_report_html_not_found(auth_client: AsyncClient):
    resp = await auth_client.get("/api/reports/nonexistent-id/html")
    assert resp.status_code == 404
