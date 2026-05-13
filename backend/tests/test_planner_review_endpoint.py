"""Planner review endpoint tests — ADR-199 (Ato 3 T-12 stub)."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


def _endpoint(workspace_id: str, report_id: str = "any-report-id") -> str:
    return f"/api/workspaces/{workspace_id}/reports/{report_id}/planner-review"


@pytest.mark.asyncio
async def test_endpoint_returns_404_not_generated_yet(auth_client: AsyncClient):
    """Stub do Ato 3 — sempre 404 ``not_generated_yet`` para workspace válido."""
    resp = await auth_client.get(_endpoint(auth_client.ws_id))  # type: ignore[attr-defined]

    assert resp.status_code == 404
    body = resp.json()
    # main.py traduz HTTPException(detail=dict) para body["detail"]={...}.
    assert body["detail"]["code"] == "not_generated_yet"
    assert "ainda não gerado" in body["detail"]["message"]


@pytest.mark.asyncio
async def test_endpoint_requires_workspace_membership(auth_client: AsyncClient):
    """Workspace inexistente / sem membership → 403 (ADR-072)."""
    resp = await auth_client.get(_endpoint("nonexistent-workspace-id"))

    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_endpoint_requires_authentication(client: AsyncClient):
    """Sem Authorization Bearer → 401."""
    resp = await client.get(_endpoint("any-workspace-id"))

    assert resp.status_code == 401
