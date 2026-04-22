"""Gate for `LegacyApiDeprecationMiddleware` (A6e.5 · ADR-108).

Canônico (/api/v1) não deve carregar headers de deprecação. Alias (/api)
deve anunciar Deprecation + Sunset + Link rel=successor-version.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from backend.app.core.config import settings


@pytest.mark.asyncio
async def test_canonical_prefix_has_no_deprecation_headers(client: AsyncClient):
    """GET /api/v1/auth/me em 401 ainda passa pela middleware — sem deprecation."""
    resp = await client.get(f"{settings.API_PREFIX}/auth/me")
    assert "Deprecation" not in resp.headers
    assert "Sunset" not in resp.headers


@pytest.mark.asyncio
async def test_legacy_prefix_emits_deprecation_headers(client: AsyncClient):
    """Alias /api/* anuncia o cutover planejado para F7A."""
    resp = await client.get(f"{settings.LEGACY_API_PREFIX}/auth/me")
    assert resp.headers.get("Deprecation") == "true"
    assert resp.headers.get("Sunset") == settings.LEGACY_SUNSET_DATE
    assert resp.headers.get("Link") == (f'<{settings.API_PREFIX}>; rel="successor-version"')


@pytest.mark.asyncio
async def test_non_api_paths_unaffected(client: AsyncClient):
    """Rota fora do alias (ex: /health) não carrega deprecation."""
    resp = await client.get("/health")
    assert "Deprecation" not in resp.headers
    assert "Sunset" not in resp.headers
