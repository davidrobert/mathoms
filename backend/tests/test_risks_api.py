"""HTTP endpoint tests do Risk aggregate (ADR-178 · Sprint A10.4).

Smoke + shape via httpx auth_client. Lógica de domínio coberta em
``test_risk_aggregate.py`` — aqui só validamos a borda HTTP.

Valores fictícios — CLAUDE.md §Dados sensíveis.
"""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_endpoint_list_risks_returns_empty(auth_client):
    ws_id = auth_client.ws_id  # type: ignore[attr-defined]
    resp = await auth_client.get(f"/api/workspaces/{ws_id}/risks")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload == {"risks": [], "total": 0}


@pytest.mark.asyncio
async def test_endpoint_create_risk_returns_201_and_dto(auth_client):
    ws_id = auth_client.ws_id  # type: ignore[attr-defined]
    payload = {
        "code": "morte",
        "name": "Morte do provedor",
        "rationale": "Falecimento compromete renda — fictício.",
        "impact_level": "crítico",
    }
    resp = await auth_client.post(f"/api/workspaces/{ws_id}/risks", json=payload)
    assert resp.status_code == 201
    body = resp.json()
    assert body["code"] == "morte"
    assert body["status"] == "Ativo"
    assert body["mitigations_decision_ids"] == []
    assert body["impact_brl"] is None


@pytest.mark.asyncio
async def test_endpoint_get_risk_404_for_nonexistent(auth_client):
    ws_id = auth_client.ws_id  # type: ignore[attr-defined]
    resp = await auth_client.get(
        f"/api/workspaces/{ws_id}/risks/00000000-0000-0000-0000-000000000000"
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_endpoint_create_duplicate_returns_409(auth_client):
    ws_id = auth_client.ws_id  # type: ignore[attr-defined]
    payload = {
        "code": "morte",
        "name": "Morte",
        "rationale": "rationale fictício suficiente",
        "impact_level": "crítico",
    }
    r1 = await auth_client.post(f"/api/workspaces/{ws_id}/risks", json=payload)
    assert r1.status_code == 201
    r2 = await auth_client.post(f"/api/workspaces/{ws_id}/risks", json=payload)
    assert r2.status_code == 409


@pytest.mark.asyncio
async def test_endpoint_patch_risk_updates(auth_client):
    ws_id = auth_client.ws_id  # type: ignore[attr-defined]
    create_payload = {
        "code": "morte",
        "name": "Morte",
        "rationale": "rationale fictício suficiente",
        "impact_level": "crítico",
    }
    created = (await auth_client.post(f"/api/workspaces/{ws_id}/risks", json=create_payload)).json()
    resp = await auth_client.patch(
        f"/api/workspaces/{ws_id}/risks/{created['id']}",
        json={"status": "Aceito", "probability": "alta"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "Aceito"
    assert body["probability"] == "alta"


@pytest.mark.asyncio
async def test_endpoint_delete_risk_204(auth_client):
    ws_id = auth_client.ws_id  # type: ignore[attr-defined]
    created = (
        await auth_client.post(
            f"/api/workspaces/{ws_id}/risks",
            json={
                "code": "morte",
                "name": "Morte",
                "rationale": "rationale fictício suficiente",
                "impact_level": "crítico",
            },
        )
    ).json()
    resp = await auth_client.delete(f"/api/workspaces/{ws_id}/risks/{created['id']}")
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_endpoint_link_mitigation_201(auth_client):
    ws_id = auth_client.ws_id  # type: ignore[attr-defined]
    risk = (
        await auth_client.post(
            f"/api/workspaces/{ws_id}/risks",
            json={
                "code": "morte",
                "name": "Morte",
                "rationale": "rationale fictício suficiente",
                "impact_level": "crítico",
            },
        )
    ).json()
    decision = (
        await auth_client.post(
            f"/api/workspaces/{ws_id}/decisions",
            json={"code": "D01", "title": "Contratar seguro fictício"},
        )
    ).json()
    resp = await auth_client.post(
        f"/api/workspaces/{ws_id}/risks/{risk['id']}/mitigations",
        json={"decision_id": decision["id"]},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["mitigations_decision_ids"] == [decision["id"]]


@pytest.mark.asyncio
async def test_endpoint_unlink_mitigation_returns_dto(auth_client):
    ws_id = auth_client.ws_id  # type: ignore[attr-defined]
    risk = (
        await auth_client.post(
            f"/api/workspaces/{ws_id}/risks",
            json={
                "code": "morte",
                "name": "Morte",
                "rationale": "rationale fictício suficiente",
                "impact_level": "crítico",
            },
        )
    ).json()
    decision = (
        await auth_client.post(
            f"/api/workspaces/{ws_id}/decisions",
            json={"code": "D01", "title": "Contratar seguro fictício"},
        )
    ).json()
    await auth_client.post(
        f"/api/workspaces/{ws_id}/risks/{risk['id']}/mitigations",
        json={"decision_id": decision["id"]},
    )
    resp = await auth_client.delete(
        f"/api/workspaces/{ws_id}/risks/{risk['id']}/mitigations/{decision['id']}"
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["mitigations_decision_ids"] == []
