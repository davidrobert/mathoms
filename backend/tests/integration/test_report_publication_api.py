"""Integration tests da Report Publications API (ADR-186)."""

from __future__ import annotations

import pytest

from backend.app.core.security import create_access_token
from backend.app.models.pipeline_artifact import PipelineArtifact
from backend.tests import factories


async def _auth(db, client):
    user = await factories.make_user(db)
    ws = await factories.make_workspace(db, owner=user)
    await db.commit()
    token = create_access_token(user.id)
    client.headers["Authorization"] = f"Bearer {token}"
    return user, ws


async def _make_artifact(db, workspace, content: dict | None = None) -> PipelineArtifact:
    run = await factories.make_run(db, workspace=workspace)
    artifact = PipelineArtifact(
        workspace_id=workspace.id,
        pipeline_run_id=run.id,
        stage="analyze_finances",
        artifact_key="analise_financeira",
        content_json=content or {"score": 78},
    )
    db.add(artifact)
    await db.flush()
    await db.commit()
    return artifact


@pytest.mark.asyncio
async def test_publish_returns_201_with_hash(db, client):
    _, ws = await _auth(db, client)
    artifact = await _make_artifact(db, ws)

    resp = await client.post(
        f"/api/workspaces/{ws.id}/reports/202601/publish",
        json={"artifact_id": artifact.id},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["workspace_id"] == ws.id
    assert body["period_yyyymm"] == "202601"
    assert body["artifact_id"] == artifact.id
    assert body["unpublished_at"] is None
    assert len(body["immutable_hash"]) == 64  # SHA-256 hex


@pytest.mark.asyncio
async def test_publish_duplicate_returns_409(db, client):
    _, ws = await _auth(db, client)
    artifact = await _make_artifact(db, ws)
    base = f"/api/workspaces/{ws.id}/reports/202601/publish"
    body = {"artifact_id": artifact.id}

    r1 = await client.post(base, json=body)
    assert r1.status_code == 201
    r2 = await client.post(base, json=body)
    assert r2.status_code == 409


@pytest.mark.asyncio
async def test_publish_unknown_artifact_returns_404(db, client):
    _, ws = await _auth(db, client)
    resp = await client.post(
        f"/api/workspaces/{ws.id}/reports/202601/publish",
        json={"artifact_id": 999_999},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_unpublish_returns_204(db, client):
    _, ws = await _auth(db, client)
    artifact = await _make_artifact(db, ws)
    base = f"/api/workspaces/{ws.id}/reports/202601/publish"

    await client.post(base, json={"artifact_id": artifact.id})
    resp = await client.delete(base)
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_unpublish_when_not_published_returns_409(db, client):
    _, ws = await _auth(db, client)
    resp = await client.delete(f"/api/workspaces/{ws.id}/reports/202601/publish")
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_get_publication_returns_live_row(db, client):
    _, ws = await _auth(db, client)
    artifact = await _make_artifact(db, ws)
    await client.post(
        f"/api/workspaces/{ws.id}/reports/202601/publish",
        json={"artifact_id": artifact.id},
    )

    resp = await client.get(f"/api/workspaces/{ws.id}/reports/202601/publication")
    assert resp.status_code == 200
    body = resp.json()
    assert body is not None
    assert body["period_yyyymm"] == "202601"


@pytest.mark.asyncio
async def test_get_publication_returns_null_when_open(db, client):
    _, ws = await _auth(db, client)
    resp = await client.get(f"/api/workspaces/{ws.id}/reports/202601/publication")
    assert resp.status_code == 200
    assert resp.json() is None


@pytest.mark.asyncio
async def test_publish_unpublish_roundtrip(db, client):
    """Cycle: publish → GET vê linha viva → unpublish → GET retorna null."""
    _, ws = await _auth(db, client)
    artifact = await _make_artifact(db, ws)
    base = f"/api/workspaces/{ws.id}/reports/202601/publish"

    await client.post(base, json={"artifact_id": artifact.id})
    r1 = await client.get(f"/api/workspaces/{ws.id}/reports/202601/publication")
    assert r1.json() is not None

    await client.delete(base)
    r2 = await client.get(f"/api/workspaces/{ws.id}/reports/202601/publication")
    assert r2.json() is None


@pytest.mark.asyncio
async def test_list_publications_returns_history(db, client):
    """Lista inclui publicação revogada + viva (mesmo período, sequência)."""
    _, ws = await _auth(db, client)
    artifact = await _make_artifact(db, ws)
    base = f"/api/workspaces/{ws.id}/reports/202601/publish"

    await client.post(base, json={"artifact_id": artifact.id})
    await client.delete(base)
    await client.post(base, json={"artifact_id": artifact.id})

    resp = await client.get(f"/api/workspaces/{ws.id}/reports/publications")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 2
    revoked = [p for p in items if p["unpublished_at"] is not None]
    live = [p for p in items if p["unpublished_at"] is None]
    assert len(revoked) == 1
    assert len(live) == 1


@pytest.mark.asyncio
async def test_publish_cross_tenant_returns_403(db, client):
    """User não-membro do workspace alheio recebe 403, não 404."""
    _, ws_a = await _auth(db, client)
    _ = await _make_artifact(db, ws_a)
    other_user = await factories.make_user(db, email="other@test.com")
    ws_b = await factories.make_workspace(db, owner=other_user)
    await db.commit()

    resp = await client.post(
        f"/api/workspaces/{ws_b.id}/reports/202601/publish",
        json={"artifact_id": 1},
    )
    assert resp.status_code == 403
