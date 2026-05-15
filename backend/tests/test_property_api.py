"""ADR-215 P4: API integration tests for /workspaces/{ws}/properties."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from backend.app.models import (
    CLASSIFICATION_LOCADO,
    CLASSIFICATION_RESIDENCIA_PRINCIPAL,
    OVERRIDE_SOURCE_USER_MANUAL,
    RESIDENCIA_STATUS_OWNED,
    RESIDENCIA_STATUS_RENTED,
    PipelineArtifact,
    PipelineRun,
    PropertyIdentity,
    WorkspacePropertyOverride,
)


async def _seed_property(db, workspace_id: str, **overrides) -> PropertyIdentity:
    defaults = dict(
        id=str(uuid.uuid4()),
        workspace_id=workspace_id,
        titular_key="david_robert",
        codigo_rfb="12",
        endereco_canonical="tasso silveira 61",
        first_seen_year=2024,
        descricao_sample="CASA - RUA TASSO DA SILVEIRA, 61 - SP",
        low_confidence=False,
    )
    defaults.update(overrides)
    p = PropertyIdentity(**defaults)
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return p


async def _seed_irpf_artifact(db, workspace_id: str, endereco: str | None) -> None:
    """Seed E1.6 artifact com `contribuinte.endereco` opcional."""
    run = PipelineRun(
        id=str(uuid.uuid4()),
        workspace_id=workspace_id,
        status="success",
    )
    db.add(run)
    await db.flush()
    content = {
        "contribuinte": {
            "cpf_masked": "***.***.***-99",
            "nome": "Test",
            "ano_base": 2024,
            "exercicio": 2025,
            "modelo": "completo",
            "natureza": "titular",
        },
        "imposto_apurado": {
            "base_calculo_brl": "0",
            "ir_devido_brl": "0",
            "deducoes_totais_brl": "0",
            "ir_pago_brl": "0",
        },
        "confidence": 0.95,
    }
    if endereco:
        content["contribuinte"]["endereco"] = endereco
    artifact = PipelineArtifact(
        workspace_id=workspace_id,
        pipeline_run_id=run.id,
        stage="extract_irpf_full",
        artifact_key="irpf_2024",
        content_json=content,
    )
    db.add(artifact)
    await db.commit()


@pytest.mark.asyncio
async def test_list_properties_empty(auth_client: AsyncClient):
    resp = await auth_client.get(f"/api/workspaces/{auth_client.ws_id}/properties")
    assert resp.status_code == 200
    data = resp.json()
    assert data["properties"] == []
    assert data["residencia_status"] == "undeclared"


@pytest.mark.asyncio
async def test_list_properties_returns_seeded_property(auth_client: AsyncClient, db):
    await _seed_property(db, auth_client.ws_id)
    resp = await auth_client.get(f"/api/workspaces/{auth_client.ws_id}/properties")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["properties"]) == 1
    p = data["properties"][0]
    assert p["titular_key"] == "david_robert"
    assert p["codigo_rfb"] == "12"
    assert p["classification"] is None
    assert p["low_confidence"] is False


@pytest.mark.asyncio
async def test_list_properties_suggests_residencia_when_irpf_endereco_matches(
    auth_client: AsyncClient, db
):
    await _seed_property(db, auth_client.ws_id)
    await _seed_irpf_artifact(
        db, auth_client.ws_id, endereco="Rua Tasso da Silveira, 61, São Paulo-SP"
    )
    resp = await auth_client.get(f"/api/workspaces/{auth_client.ws_id}/properties")
    assert resp.status_code == 200
    data = resp.json()
    p = data["properties"][0]
    assert p["suggested_score"] is not None and p["suggested_score"] >= 80
    assert p["suggested_residencia_principal"] is True


@pytest.mark.asyncio
async def test_list_properties_no_suggestion_when_irpf_endereco_absent(
    auth_client: AsyncClient, db
):
    await _seed_property(db, auth_client.ws_id)
    await _seed_irpf_artifact(db, auth_client.ws_id, endereco=None)
    resp = await auth_client.get(f"/api/workspaces/{auth_client.ws_id}/properties")
    data = resp.json()
    p = data["properties"][0]
    assert p["suggested_residencia_principal"] is False


@pytest.mark.asyncio
async def test_put_classification_owned_status_auto_set(auth_client: AsyncClient, db):
    p = await _seed_property(db, auth_client.ws_id)
    resp = await auth_client.put(
        f"/api/workspaces/{auth_client.ws_id}/properties/{p.id}/classification",
        json={
            "classification": CLASSIFICATION_RESIDENCIA_PRINCIPAL,
            "override_source": OVERRIDE_SOURCE_USER_MANUAL,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["classification"] == CLASSIFICATION_RESIDENCIA_PRINCIPAL

    # Side-effect: residencia_status flippa para owned.
    list_resp = await auth_client.get(f"/api/workspaces/{auth_client.ws_id}/properties")
    assert list_resp.json()["residencia_status"] == RESIDENCIA_STATUS_OWNED


@pytest.mark.asyncio
async def test_put_classification_locado_does_not_change_status(auth_client: AsyncClient, db):
    p = await _seed_property(db, auth_client.ws_id)
    resp = await auth_client.put(
        f"/api/workspaces/{auth_client.ws_id}/properties/{p.id}/classification",
        json={"classification": CLASSIFICATION_LOCADO},
    )
    assert resp.status_code == 200

    list_resp = await auth_client.get(f"/api/workspaces/{auth_client.ws_id}/properties")
    assert list_resp.json()["residencia_status"] == "undeclared"


@pytest.mark.asyncio
async def test_put_classification_idempotent(auth_client: AsyncClient, db):
    p = await _seed_property(db, auth_client.ws_id)
    for _ in range(3):
        resp = await auth_client.put(
            f"/api/workspaces/{auth_client.ws_id}/properties/{p.id}/classification",
            json={"classification": CLASSIFICATION_LOCADO},
        )
        assert resp.status_code == 200


@pytest.mark.asyncio
async def test_put_classification_invalid_returns_422(auth_client: AsyncClient, db):
    p = await _seed_property(db, auth_client.ws_id)
    resp = await auth_client.put(
        f"/api/workspaces/{auth_client.ws_id}/properties/{p.id}/classification",
        json={"classification": "garbage"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_put_classification_unknown_property_returns_404(auth_client: AsyncClient):
    resp = await auth_client.put(
        f"/api/workspaces/{auth_client.ws_id}/properties/non-existent/classification",
        json={"classification": CLASSIFICATION_LOCADO},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_put_residencia_status_rented_clears_residencia_overrides(
    auth_client: AsyncClient, db
):
    from sqlalchemy import select

    p = await _seed_property(db, auth_client.ws_id)
    # Marca residencia_principal primeiro.
    await auth_client.put(
        f"/api/workspaces/{auth_client.ws_id}/properties/{p.id}/classification",
        json={"classification": CLASSIFICATION_RESIDENCIA_PRINCIPAL},
    )
    # Mudar para rented apaga.
    resp = await auth_client.put(
        f"/api/workspaces/{auth_client.ws_id}/residencia-status",
        json={"status": RESIDENCIA_STATUS_RENTED},
    )
    assert resp.status_code == 200

    db.expire_all()
    remaining = (
        await db.execute(
            select(WorkspacePropertyOverride).where(
                WorkspacePropertyOverride.workspace_id == auth_client.ws_id,
                WorkspacePropertyOverride.classification == CLASSIFICATION_RESIDENCIA_PRINCIPAL,
            )
        )
    ).all()
    assert remaining == []


@pytest.mark.asyncio
async def test_put_residencia_status_invalid_returns_422(auth_client: AsyncClient):
    resp = await auth_client.put(
        f"/api/workspaces/{auth_client.ws_id}/residencia-status",
        json={"status": "weird"},
    )
    assert resp.status_code == 422
