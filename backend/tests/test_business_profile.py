"""Workspace.business_profile_json — endpoint + Pydantic (Sprint A10.7 + A16) — valores fictícios CLAUDE.md."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from backend.app.schemas.business_profile import BusinessProfile

# ────────── Pydantic shape — campos A10.7 ──────────


def test_business_profile_all_optional() -> None:
    """Workspace recém-criado: todos os campos opcionais; default None."""
    bp = BusinessProfile()
    assert bp.contador is None
    assert bp.regime is None
    assert bp.holding_prazo_meses is None
    # Campos A16 também default None.
    assert bp.anexo_simples is None
    assert bp.iss_aliquota_pct is None
    assert bp.cnae_principal is None
    assert bp.tipo_declaracao_ir is None


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


# ────────── Pydantic shape — campos A16 (ADR-236 §D1) ──────────


def test_business_profile_accepts_valid_anexo_simples() -> None:
    """Anexos III/V aceitos via Literal."""
    for anexo in ("III", "V"):
        bp = BusinessProfile(anexo_simples=anexo)  # type: ignore[arg-type]
        assert bp.anexo_simples == anexo


def test_business_profile_rejects_unknown_anexo_simples() -> None:
    """Anexo fora de {III, V} dispara ValidationError (V1 só cobre serviços)."""
    with pytest.raises(ValidationError):
        BusinessProfile(anexo_simples="I")  # type: ignore[arg-type]
    with pytest.raises(ValidationError):
        BusinessProfile(anexo_simples="IV")  # type: ignore[arg-type]


def test_business_profile_iss_aliquota_within_lc_116_range() -> None:
    """ISS 2-5% — limites Lei Complementar 116/2003."""
    for pct in (2.0, 3.5, 5.0):
        bp = BusinessProfile(iss_aliquota_pct=pct)
        assert bp.iss_aliquota_pct == pct


def test_business_profile_iss_aliquota_below_2pct_rejected() -> None:
    with pytest.raises(ValidationError):
        BusinessProfile(iss_aliquota_pct=1.99)


def test_business_profile_iss_aliquota_above_5pct_rejected() -> None:
    with pytest.raises(ValidationError):
        BusinessProfile(iss_aliquota_pct=5.01)


def test_business_profile_cnae_principal_accepts_string() -> None:
    """CNAE 7-dígitos — formato 'NNNN-N/NN' (validação leve via max_length)."""
    bp = BusinessProfile(cnae_principal="6201-5/01")
    assert bp.cnae_principal == "6201-5/01"


def test_business_profile_cnae_principal_above_max_length_rejected() -> None:
    with pytest.raises(ValidationError):
        BusinessProfile(cnae_principal="6201-5/01-extra-bytes")


def test_business_profile_accepts_valid_tipo_declaracao_ir() -> None:
    for tipo in ("completa", "simplificada"):
        bp = BusinessProfile(tipo_declaracao_ir=tipo)  # type: ignore[arg-type]
        assert bp.tipo_declaracao_ir == tipo


def test_business_profile_rejects_unknown_tipo_declaracao_ir() -> None:
    with pytest.raises(ValidationError):
        BusinessProfile(tipo_declaracao_ir="dispensado")  # type: ignore[arg-type]


def test_business_profile_a16_fields_combine_with_a10_7_fields() -> None:
    """Round-trip de todos os 7 campos juntos — paridade de shape."""
    bp = BusinessProfile(
        contador="Fictício LTDA",
        regime="simples",
        holding_prazo_meses=24,
        anexo_simples="III",
        iss_aliquota_pct=3.0,
        cnae_principal="6201-5/01",
        tipo_declaracao_ir="completa",
    )
    assert bp.contador == "Fictício LTDA"
    assert bp.regime == "simples"
    assert bp.holding_prazo_meses == 24
    assert bp.anexo_simples == "III"
    assert bp.iss_aliquota_pct == 3.0
    assert bp.cnae_principal == "6201-5/01"
    assert bp.tipo_declaracao_ir == "completa"


# ────────── Endpoints HTTP ──────────

_EMPTY_PROFILE_RESPONSE = {
    "contador": None,
    "regime": None,
    "holding_prazo_meses": None,
    "anexo_simples": None,
    "iss_aliquota_pct": None,
    "cnae_principal": None,
    "tipo_declaracao_ir": None,
}


def _with_defaults(**overrides) -> dict:
    """Builda payload `BusinessProfile` partindo de tudo None."""
    return {**_EMPTY_PROFILE_RESPONSE, **overrides}


@pytest.mark.asyncio
async def test_endpoint_get_business_profile_returns_empty_default(auth_client):
    ws_id = auth_client.ws_id  # type: ignore[attr-defined]
    resp = await auth_client.get(f"/api/workspaces/{ws_id}/business-profile")
    assert resp.status_code == 200
    body = resp.json()
    assert body == _EMPTY_PROFILE_RESPONSE


@pytest.mark.asyncio
async def test_endpoint_patch_business_profile_persists(auth_client):
    ws_id = auth_client.ws_id  # type: ignore[attr-defined]
    payload = _with_defaults(
        contador="Contador Fictício LTDA",
        regime="lucro_presumido",
        holding_prazo_meses=24,
        tipo_declaracao_ir="completa",
    )
    resp = await auth_client.patch(f"/api/workspaces/{ws_id}/business-profile", json=payload)
    assert resp.status_code == 200
    assert resp.json() == payload

    get_resp = await auth_client.get(f"/api/workspaces/{ws_id}/business-profile")
    assert get_resp.json() == payload


@pytest.mark.asyncio
async def test_endpoint_patch_business_profile_a16_full(auth_client):
    """Workspace consultor preenche todos os campos A16 — round-trip íntegro."""
    ws_id = auth_client.ws_id  # type: ignore[attr-defined]
    payload = _with_defaults(
        contador="Contabilidade Fictícia ME",
        regime="simples",
        holding_prazo_meses=12,
        anexo_simples="III",
        iss_aliquota_pct=3.0,
        cnae_principal="6201-5/01",
        tipo_declaracao_ir="completa",
    )
    resp = await auth_client.patch(f"/api/workspaces/{ws_id}/business-profile", json=payload)
    assert resp.status_code == 200
    assert resp.json() == payload


@pytest.mark.asyncio
async def test_endpoint_patch_business_profile_partial_clears_other_fields(auth_client):
    """PATCH é replace (shape simples). Campo omitido vira None — comportamento documentado."""
    ws_id = auth_client.ws_id  # type: ignore[attr-defined]
    full = _with_defaults(contador="Foo Contador", regime="mei", holding_prazo_meses=12)
    await auth_client.patch(f"/api/workspaces/{ws_id}/business-profile", json=full)
    resp = await auth_client.patch(
        f"/api/workspaces/{ws_id}/business-profile",
        json={"regime": "lucro_real"},
    )
    assert resp.status_code == 200
    assert resp.json() == _with_defaults(regime="lucro_real")


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
async def test_endpoint_patch_rejects_invalid_anexo_simples(auth_client):
    ws_id = auth_client.ws_id  # type: ignore[attr-defined]
    resp = await auth_client.patch(
        f"/api/workspaces/{ws_id}/business-profile",
        json={"anexo_simples": "VI"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_endpoint_patch_rejects_iss_out_of_range(auth_client):
    ws_id = auth_client.ws_id  # type: ignore[attr-defined]
    resp = await auth_client.patch(
        f"/api/workspaces/{ws_id}/business-profile",
        json={"iss_aliquota_pct": 7.0},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_endpoint_patch_rejects_invalid_tipo_declaracao_ir(auth_client):
    ws_id = auth_client.ws_id  # type: ignore[attr-defined]
    resp = await auth_client.patch(
        f"/api/workspaces/{ws_id}/business-profile",
        json={"tipo_declaracao_ir": "dispensado"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_endpoint_business_profile_round_trip(auth_client):
    """PATCH → GET retorna shape integral; round-trip de persistência."""
    ws_id = auth_client.ws_id  # type: ignore[attr-defined]
    payload = _with_defaults(
        contador="Persist Check",
        regime="mei",
        holding_prazo_meses=6,
        tipo_declaracao_ir="simplificada",
    )
    patch_resp = await auth_client.patch(f"/api/workspaces/{ws_id}/business-profile", json=payload)
    assert patch_resp.status_code == 200

    # Segundo GET prova que o JSON foi persistido (não retornado só do response do PATCH).
    get_resp = await auth_client.get(f"/api/workspaces/{ws_id}/business-profile")
    assert get_resp.status_code == 200
    assert get_resp.json() == payload
