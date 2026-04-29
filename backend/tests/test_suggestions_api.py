"""Testes de integração da API de Suggestions (ADR-153).

Cobrem:
- GET list/count com filtro de status
- GET 404 para id desconhecido
- POST accept cria Decision e marca Aceita (201/200)
- POST modify cria Decision com overrides e marca Modificada
- POST dismiss persiste reason
- 409 ao operar sobre Suggestion não-Pendente
- 422 com reason inválido
- POST regenerate-suggestions é idempotente (skip por dedup)
"""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.security import create_access_token
from backend.app.models.pipeline_artifact import PipelineArtifact
from backend.app.models.suggestion import Suggestion
from backend.tests import factories


async def _seed_pending_in_ws(
    db: AsyncSession, workspace_id: str, *, dedup_key: str = "k" * 32
) -> Suggestion:
    s = Suggestion(
        workspace_id=workspace_id,
        section_id="S2",
        kind="reserva_insuficiente",
        origin="deterministic",
        severity="warning",
        title="Reforçar reserva",
        rationale="Cobertura insuficiente",
        amount_brl_cents=500_000,
        dedup_key=dedup_key,
        status="Pendente",
    )
    db.add(s)
    await db.flush()
    return s


async def _make_auth(db, client):
    user = await factories.make_user(db)
    ws = await factories.make_workspace(db, owner=user)
    await db.commit()
    token = create_access_token(user.id)
    client.headers["Authorization"] = f"Bearer {token}"
    return user, ws


@pytest.mark.asyncio
async def test_list_returns_total(db, client):
    _, ws = await _make_auth(db, client)
    await _seed_pending_in_ws(db, ws.id, dedup_key="A" * 32)
    await _seed_pending_in_ws(db, ws.id, dedup_key="B" * 32)
    await db.commit()

    resp = await client.get(f"/api/workspaces/{ws.id}/suggestions")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2


@pytest.mark.asyncio
async def test_count_default_pendente(db, client):
    _, ws = await _make_auth(db, client)
    await _seed_pending_in_ws(db, ws.id)
    await db.commit()

    resp = await client.get(f"/api/workspaces/{ws.id}/suggestions/count")
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 1
    assert body["status"] == "Pendente"


@pytest.mark.asyncio
async def test_count_with_explicit_status(db, client):
    _, ws = await _make_auth(db, client)
    await _seed_pending_in_ws(db, ws.id)
    await db.commit()

    resp = await client.get(f"/api/workspaces/{ws.id}/suggestions/count?status=Descartada")
    assert resp.status_code == 200
    assert resp.json()["count"] == 0


@pytest.mark.asyncio
async def test_get_404_for_unknown(db, client):
    _, ws = await _make_auth(db, client)
    resp = await client.get(
        f"/api/workspaces/{ws.id}/suggestions/00000000-0000-0000-0000-000000000000"
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_accept_creates_decision_returns_aceita(db, client):
    _, ws = await _make_auth(db, client)
    s = await _seed_pending_in_ws(db, ws.id)
    await db.commit()

    resp = await client.post(
        f"/api/workspaces/{ws.id}/suggestions/{s.id}/accept",
        json={"decision_code": "D01"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "Aceita"
    assert body["accepted_decision_id"] is not None

    decisions_resp = await client.get(f"/api/workspaces/{ws.id}/decisions")
    decision_codes = [d["code"] for d in decisions_resp.json()["decisions"]]
    assert "D01" in decision_codes


@pytest.mark.asyncio
async def test_modify_creates_decision_with_overrides(db, client):
    _, ws = await _make_auth(db, client)
    s = await _seed_pending_in_ws(db, ws.id)
    await db.commit()

    resp = await client.post(
        f"/api/workspaces/{ws.id}/suggestions/{s.id}/modify",
        json={
            "decision_code": "D02",
            "title": "Customizado",
            "amount_brl": "9999.99",
        },
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "Modificada"

    dec_resp = await client.get(f"/api/workspaces/{ws.id}/decisions")
    target = next(d for d in dec_resp.json()["decisions"] if d["code"] == "D02")
    assert target["title"] == "Customizado"
    assert target["amount_brl"] == "9999.99"


@pytest.mark.asyncio
async def test_dismiss_with_reason(db, client):
    _, ws = await _make_auth(db, client)
    s = await _seed_pending_in_ws(db, ws.id)
    await db.commit()

    resp = await client.post(
        f"/api/workspaces/{ws.id}/suggestions/{s.id}/dismiss",
        json={"reason": "ja_considerei"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "Descartada"
    assert body["dismissed_reason"] == "ja_considerei"


@pytest.mark.asyncio
async def test_dismiss_already_terminal_returns_409(db, client):
    _, ws = await _make_auth(db, client)
    s = await _seed_pending_in_ws(db, ws.id)
    await db.commit()
    await client.post(
        f"/api/workspaces/{ws.id}/suggestions/{s.id}/dismiss",
        json={"reason": "adiar"},
    )
    second = await client.post(
        f"/api/workspaces/{ws.id}/suggestions/{s.id}/dismiss",
        json={"reason": "outro"},
    )
    assert second.status_code == 409


@pytest.mark.asyncio
async def test_dismiss_invalid_reason_returns_422(db, client):
    _, ws = await _make_auth(db, client)
    s = await _seed_pending_in_ws(db, ws.id)
    await db.commit()
    resp = await client.post(
        f"/api/workspaces/{ws.id}/suggestions/{s.id}/dismiss",
        json={"reason": "fake_reason"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_regenerate_suggestions_idempotent(db, client):
    """E2E: snapshot com gatilho de reserva insuficiente → 1 sugestão criada
    no primeiro run; segundo run não duplica (dedup)."""
    user, ws = await _make_auth(db, client)
    run = await factories.make_run(db, workspace=ws)
    artifact = PipelineArtifact(
        workspace_id=ws.id,
        pipeline_run_id=run.id,
        stage="E5",
        artifact_key="analise_financeira",
        content_json={
            "reserva_emergencia": {
                "meses_cobertura": 1.0,
                "gap_brl": 9000.0,
            },
        },
    )
    db.add(artifact)
    await db.flush()
    report = await factories.make_report(
        db, workspace=ws, pipeline_run=run, analysis_artifact_id=artifact.id
    )
    await db.commit()

    base = f"/api/workspaces/{ws.id}/reports/{report.id}/regenerate-suggestions"
    resp1 = await client.post(base, json={})
    assert resp1.status_code == 200, resp1.text
    body1 = resp1.json()
    assert body1["created"] == 1
    assert body1["skipped_dedup"] == 0

    resp2 = await client.post(base, json={})
    assert resp2.status_code == 200
    body2 = resp2.json()
    assert body2["created"] == 0
    assert body2["skipped_dedup"] == 1

    # E confirma que ainda há só 1 Pendente.
    list_resp = await client.get(f"/api/workspaces/{ws.id}/suggestions?status=Pendente")
    assert list_resp.json()["total"] == 1
