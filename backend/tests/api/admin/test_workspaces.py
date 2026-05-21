"""Testes de /admin/workspaces/{id}/business-profile (ADR-236 P1).

Operador (consultor) preenche `BusinessProfile` via console interno sem
ser membro do workspace; replace, não merge; audit log gravado.
"""

from __future__ import annotations

import pytest

from backend.tests.factories.builders import make_workspace

_EMPTY_PROFILE = {
    "contador": None,
    "regime": None,
    "holding_prazo_meses": None,
    "anexo_simples": None,
    "iss_aliquota_pct": None,
    "cnae_principal": None,
    "tipo_declaracao_ir": None,
}


def _with_defaults(**overrides) -> dict:
    return {**_EMPTY_PROFILE, **overrides}


async def _with_cookie(client, token: str) -> None:
    client.cookies.set("ops_session", token, domain="test", path="/admin")


@pytest.mark.asyncio
async def test_admin_get_returns_empty_default(
    ops_session_token_superadmin, admin_ui_enabled, ops_yaml, client, db
) -> None:
    ws = await make_workspace(db)
    await db.commit()
    await _with_cookie(client, ops_session_token_superadmin)
    resp = await client.get(f"/admin/workspaces/{ws.id}/business-profile")
    assert resp.status_code == 200
    assert resp.json() == _EMPTY_PROFILE


@pytest.mark.asyncio
async def test_admin_get_404_for_unknown_workspace(
    ops_session_token_superadmin, admin_ui_enabled, ops_yaml, client
) -> None:
    await _with_cookie(client, ops_session_token_superadmin)
    resp = await client.get("/admin/workspaces/nonexistent/business-profile")
    assert resp.status_code == 404


def _full_a16_payload() -> dict:
    return _with_defaults(
        contador="Contabilidade Fictícia ME",
        regime="simples",
        holding_prazo_meses=18,
        anexo_simples="III",
        iss_aliquota_pct=3.0,
        cnae_principal="6201-5/01",
        tipo_declaracao_ir="completa",
    )


@pytest.mark.asyncio
async def test_admin_patch_persists_full_a16_payload(
    ops_session_token_ops, admin_ui_enabled, ops_yaml, audit_path, client, db
) -> None:
    """Operator (não-superadmin) preenche todos os 7 campos — round-trip + audit."""
    ws = await make_workspace(db)
    await db.commit()
    payload = _full_a16_payload()

    await _with_cookie(client, ops_session_token_ops)
    resp = await client.patch(f"/admin/workspaces/{ws.id}/business-profile", json=payload)
    assert resp.status_code == 200
    assert resp.json() == payload
    assert (await client.get(f"/admin/workspaces/{ws.id}/business-profile")).json() == payload

    audit_text = audit_path.read_text(encoding="utf-8")
    assert "workspace.update_business_profile" in audit_text
    assert ws.id in audit_text


@pytest.mark.asyncio
async def test_admin_patch_replaces_not_merges(
    ops_session_token_superadmin, admin_ui_enabled, ops_yaml, audit_path, client, db
) -> None:
    """PATCH replace: 2ª chamada parcial limpa campos omitidos."""
    ws = await make_workspace(db)
    await db.commit()
    await _with_cookie(client, ops_session_token_superadmin)
    full = _with_defaults(contador="Foo Contador", regime="mei", holding_prazo_meses=6)
    await client.patch(f"/admin/workspaces/{ws.id}/business-profile", json=full)

    resp = await client.patch(
        f"/admin/workspaces/{ws.id}/business-profile",
        json={"regime": "lucro_presumido"},
    )
    assert resp.status_code == 200
    assert resp.json() == _with_defaults(regime="lucro_presumido")


@pytest.mark.asyncio
async def test_admin_patch_404_for_unknown_workspace(
    ops_session_token_superadmin, admin_ui_enabled, ops_yaml, audit_path, client
) -> None:
    await _with_cookie(client, ops_session_token_superadmin)
    resp = await client.patch(
        "/admin/workspaces/nonexistent/business-profile",
        json={"regime": "mei"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_admin_patch_rejects_invalid_anexo_simples(
    ops_session_token_superadmin, admin_ui_enabled, ops_yaml, audit_path, client, db
) -> None:
    ws = await make_workspace(db)
    await db.commit()
    await _with_cookie(client, ops_session_token_superadmin)
    resp = await client.patch(
        f"/admin/workspaces/{ws.id}/business-profile",
        json={"anexo_simples": "I"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_admin_patch_rejects_iss_out_of_range(
    ops_session_token_superadmin, admin_ui_enabled, ops_yaml, audit_path, client, db
) -> None:
    ws = await make_workspace(db)
    await db.commit()
    await _with_cookie(client, ops_session_token_superadmin)
    resp = await client.patch(
        f"/admin/workspaces/{ws.id}/business-profile",
        json={"iss_aliquota_pct": 0.5},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_admin_patch_rejects_extra_field(
    ops_session_token_superadmin, admin_ui_enabled, ops_yaml, audit_path, client, db
) -> None:
    ws = await make_workspace(db)
    await db.commit()
    await _with_cookie(client, ops_session_token_superadmin)
    resp = await client.patch(
        f"/admin/workspaces/{ws.id}/business-profile",
        json={"contador": "ok", "ramo_atividade": "extra-forbidden"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_admin_endpoints_require_ops_session(client, admin_ui_enabled, ops_yaml, db) -> None:
    """Sem cookie ops_session → 401, mesmo com workspace existente."""
    ws = await make_workspace(db)
    await db.commit()
    resp_get = await client.get(f"/admin/workspaces/{ws.id}/business-profile")
    assert resp_get.status_code == 401
    resp_patch = await client.patch(
        f"/admin/workspaces/{ws.id}/business-profile",
        json={"regime": "mei"},
    )
    assert resp_patch.status_code == 401
