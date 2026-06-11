"""GET /llm/models + model_status + providers novos (ADR-288 F1)."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_llm_models_default_provider(auth_client: AsyncClient):
    """Sem query param retorna catálogo anthropic com default e pricing."""
    resp = await auth_client.get(f"/api/workspaces/{auth_client.ws_id}/config/llm/models")
    assert resp.status_code == 200
    body = resp.json()
    assert body["provider"] == "anthropic"
    assert body["fetched_dynamic"] is False
    assert body["default_model"] == "claude-sonnet-4-6"
    values = [m["value"] for m in body["models"]]
    assert "claude-opus-4-8" in values
    assert body["default_model"] in values
    assert all(m["source"] == "curated" for m in body["models"])
    assert all(m["pricing_known"] for m in body["models"])


@pytest.mark.asyncio
async def test_llm_models_provider_invalido(auth_client: AsyncClient):
    resp = await auth_client.get(
        f"/api/workspaces/{auth_client.ws_id}/config/llm/models?provider=nope"
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_llm_models_google_sem_hack_de_prefixo(auth_client: AsyncClient):
    """Values do Google são IDs puros — prefixo gemini/ é do adapter LiteLLM."""
    resp = await auth_client.get(
        f"/api/workspaces/{auth_client.ws_id}/config/llm/models?provider=google"
    )
    assert resp.status_code == 200
    values = [m["value"] for m in resp.json()["models"]]
    assert values and all(not v.startswith("gemini/") for v in values)


@pytest.mark.asyncio
async def test_save_provider_google_e_openrouter_aceitos(auth_client: AsyncClient):
    """google/openrouter passavam 422 antes da ADR-288."""
    for provider, model in (("google", "gemini-2.5-flash"), ("openrouter", "openai/gpt-5")):
        resp = await auth_client.put(
            f"/api/workspaces/{auth_client.ws_id}/config/llm",
            json={"provider": provider, "api_key": "sk-test", "model_name": model},
        )
        assert resp.status_code == 200, (provider, resp.text)
        assert resp.json()["provider"] == provider


@pytest.mark.asyncio
async def test_model_status_deprecated_no_response(auth_client: AsyncClient):
    """Modelo com EOL anunciado sinaliza model_status=deprecated (sem migration)."""
    resp = await auth_client.put(
        f"/api/workspaces/{auth_client.ws_id}/config/llm",
        json={
            "provider": "anthropic",
            "api_key": "sk-test",
            "model_name": "claude-sonnet-4-20250514",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["model_status"] == "deprecated"

    resp = await auth_client.put(
        f"/api/workspaces/{auth_client.ws_id}/config/llm",
        json={"provider": "anthropic", "api_key": "sk-test", "model_name": "claude-sonnet-4-6"},
    )
    assert resp.json()["model_status"] == "ok"
