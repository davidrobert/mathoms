"""Workspace.business_profile_json — endpoint + Pydantic (Sprint A10.7) — valores fictícios CLAUDE.md."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from backend.app.schemas.business_profile import BusinessProfile

# ────────── Pydantic shape ──────────


def test_business_profile_all_optional() -> None:
    """Workspace recém-criado: todos os campos opcionais; default None."""
    bp = BusinessProfile()
    assert bp.contador is None
    assert bp.regime is None
    assert bp.holding_prazo_meses is None


def test_business_profile_accepts_valid_regimes() -> None:
    """4 regimes aceitos via Literal — não falha em construção."""
    for regime in ("mei", "lucro_presumido", "lucro_real", "simples"):
        bp = BusinessProfile(regime=regime)  # type: ignore[arg-type]
        assert bp.regime == regime


def test_business_profile_rejects_unknown_regime() -> None:
    """Regime fora do enum dispara ValidationError."""
    with pytest.raises(ValidationError):
        BusinessProfile(regime="ltda")  # type: ignore[arg-type]


def test_business_profile_holding_prazo_negative_rejected() -> None:
    with pytest.raises(ValidationError):
        BusinessProfile(holding_prazo_meses=-1)


def test_business_profile_holding_prazo_above_240_rejected() -> None:
    with pytest.raises(ValidationError):
        BusinessProfile(holding_prazo_meses=241)


def test_business_profile_extra_field_forbidden() -> None:
    """`extra=forbid` impede campos não declarados — sanity de shape."""
    with pytest.raises(ValidationError):
        BusinessProfile(unknown_field="foo")  # type: ignore[call-arg]


# ────────── Endpoints HTTP ──────────


@pytest.mark.asyncio
async def test_endpoint_get_business_profile_returns_empty_default(auth_client):
    ws_id = auth_client.ws_id  # type: ignore[attr-defined]
    resp = await auth_client.get(f"/api/workspaces/{ws_id}/business-profile")
    assert resp.status_code == 200
    body = resp.json()
    assert body == {"contador": None, "regime": None, "holding_prazo_meses": None}


@pytest.mark.asyncio
async def test_endpoint_patch_business_profile_persists(auth_client):
    ws_id = auth_client.ws_id  # type: ignore[attr-defined]
    payload = {
        "contador": "Contador Fictício LTDA",
        "regime": "lucro_presumido",
        "holding_prazo_meses": 24,
    }
    resp = await auth_client.patch(
        f"/api/workspaces/{ws_id}/business-profile",
        json=payload,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body == payload

    get_resp = await auth_client.get(f"/api/workspaces/{ws_id}/business-profile")
    assert get_resp.json() == payload


@pytest.mark.asyncio
async def test_endpoint_patch_business_profile_partial_clears_other_fields(auth_client):
    """PATCH é replace (shape simples). Campo omitido vira None — comportamento documentado."""
    ws_id = auth_client.ws_id  # type: ignore[attr-defined]
    full = {"contador": "Foo Contador", "regime": "mei", "holding_prazo_meses": 12}
    await auth_client.patch(f"/api/workspaces/{ws_id}/business-profile", json=full)
    resp = await auth_client.patch(
        f"/api/workspaces/{ws_id}/business-profile",
        json={"regime": "lucro_real"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body == {"contador": None, "regime": "lucro_real", "holding_prazo_meses": None}


@pytest.mark.asyncio
async def test_endpoint_patch_rejects_invalid_regime(auth_client):
    ws_id = auth_client.ws_id  # type: ignore[attr-defined]
    resp = await auth_client.patch(
        f"/api/workspaces/{ws_id}/business-profile",
        json={"regime": "regime_inexistente"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_endpoint_patch_rejects_negative_holding_prazo(auth_client):
    ws_id = auth_client.ws_id  # type: ignore[attr-defined]
    resp = await auth_client.patch(
        f"/api/workspaces/{ws_id}/business-profile",
        json={"holding_prazo_meses": -5},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_endpoint_patch_rejects_extra_field(auth_client):
    ws_id = auth_client.ws_id  # type: ignore[attr-defined]
    resp = await auth_client.patch(
        f"/api/workspaces/{ws_id}/business-profile",
        json={"contador": "ok", "ramo_atividade": "extra-field-forbidden"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_endpoint_business_profile_round_trip(auth_client):
    """PATCH → GET retorna shape integral; round-trip de persistência."""
    ws_id = auth_client.ws_id  # type: ignore[attr-defined]
    payload = {"contador": "Persist Check", "regime": "mei", "holding_prazo_meses": 6}
    patch_resp = await auth_client.patch(f"/api/workspaces/{ws_id}/business-profile", json=payload)
    assert patch_resp.status_code == 200

    # Segundo GET prova que o JSON foi persistido (não retornado só do response do PATCH).
    get_resp = await auth_client.get(f"/api/workspaces/{ws_id}/business-profile")
    assert get_resp.status_code == 200
    assert get_resp.json() == payload
