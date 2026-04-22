"""Tests for report endpoints — list, get, html, data (F9 · ADR-076)."""

import json
import uuid
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_list_reports_empty(auth_client: AsyncClient):
    resp = await auth_client.get(f"/api/workspaces/{auth_client.ws_id}/reports")
    assert resp.status_code == 200
    data = resp.json()
    assert data["reports"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_list_reports_unauthorized(client: AsyncClient):
    resp = await client.get("/api/workspaces/00000000-0000-0000-0000-000000000000/reports")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_get_report_not_found(auth_client: AsyncClient):
    resp = await auth_client.get(f"/api/workspaces/{auth_client.ws_id}/reports/nonexistent-id")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_report_html_not_found(auth_client: AsyncClient):
    resp = await auth_client.get(f"/api/workspaces/{auth_client.ws_id}/reports/nonexistent-id/html")
    assert resp.status_code == 404


# ─── F9 · ADR-076: analysis JSON endpoint ──────────────────────────────


async def _seed_report(
    auth_client: AsyncClient,
    *,
    html_content: str = "<html><body>ok</body></html>",
    analysis_payload: dict | None = None,
    pipeline_run_id: str | None = None,
    premissas_snapshot_json: dict | None = None,
    tmp_path: Path,
    db: AsyncSession | None = None,
) -> str:
    """Cria um Report vinculado ao workspace do auth_client e retorna seu id.

    Escreve HTML e (opcionalmente) o JSON de análise em `tmp_path` para que
    os endpoints possam servir os arquivos.

    ``db`` — deve ser a fixture ``db`` do conftest. Usar TestSession()
    direto causa "no such table" em pytest-asyncio strict mode porque a
    session é criada fora do lifecycle de fixtures.
    """
    from backend.app.models.report import Report
    from backend.app.models.workspace import Workspace

    html_file = tmp_path / "report.html"
    html_file.write_text(html_content, encoding="utf-8")

    analysis_path: Path | None = None
    if analysis_payload is not None:
        analysis_path = tmp_path / "analysis.json"
        analysis_path.write_text(json.dumps(analysis_payload), encoding="utf-8")

    # Use the fixture-managed session (same lifecycle as setup_db/create_all).
    # Falls back to TestSession if db not provided (compat).
    if db is None:
        from backend.tests.conftest import TestSession

        session_ctx = TestSession()
    else:
        # Wrap the db fixture in a no-op context manager so we can use the
        # same ``async with`` pattern.
        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def _passthrough():
            yield db

        session_ctx = _passthrough()

    async with session_ctx as session:
        ws = (await session.execute(select(Workspace))).scalar_one()
        report = Report(
            id=str(uuid.uuid4()),
            workspace_id=ws.id,
            pipeline_run_id=pipeline_run_id,
            title="Relatório de Teste",
            html_path=str(html_file),
            analysis_json_path=str(analysis_path) if analysis_path else None,
            size_bytes=len(html_content),
            premissas_snapshot_json=premissas_snapshot_json,
        )
        session.add(report)
        await session.commit()
        return report.id


@pytest.mark.asyncio
async def test_get_report_includes_has_analysis_data_true(
    auth_client: AsyncClient, tmp_path: Path, db: AsyncSession
):
    rid = await _seed_report(
        auth_client,
        analysis_payload={"periodo_dados": "202601-202604", "patrimonio": {}},
        tmp_path=tmp_path,
        db=db,
    )
    resp = await auth_client.get(f"/api/workspaces/{auth_client.ws_id}/reports/{rid}")
    assert resp.status_code == 200
    assert resp.json()["has_analysis_data"] is True


@pytest.mark.asyncio
async def test_get_report_has_analysis_data_false_when_no_json(
    auth_client: AsyncClient, tmp_path: Path, db: AsyncSession
):
    rid = await _seed_report(auth_client, analysis_payload=None, tmp_path=tmp_path, db=db)
    resp = await auth_client.get(f"/api/workspaces/{auth_client.ws_id}/reports/{rid}")
    assert resp.status_code == 200
    assert resp.json()["has_analysis_data"] is False


@pytest.mark.asyncio
async def test_get_report_includes_source_document_fields(
    auth_client: AsyncClient, tmp_path: Path, db: AsyncSession
):
    rid = await _seed_report(
        auth_client,
        analysis_payload={"x": 1},
        tmp_path=tmp_path,
        db=db,
    )
    resp = await auth_client.get(f"/api/workspaces/{auth_client.ws_id}/reports/{rid}")
    assert resp.status_code == 200
    data = resp.json()
    assert "source_document_count" in data
    assert "source_document_ids" in data
    assert isinstance(data["source_document_ids"], list)


@pytest.mark.asyncio
async def test_get_report_includes_pipeline_run_id(
    auth_client: AsyncClient, tmp_path: Path, db: AsyncSession
):
    run_id = str(uuid.uuid4())
    rid = await _seed_report(
        auth_client,
        analysis_payload=None,
        pipeline_run_id=run_id,
        tmp_path=tmp_path,
        db=db,
    )
    resp = await auth_client.get(f"/api/workspaces/{auth_client.ws_id}/reports/{rid}")
    assert resp.status_code == 200
    assert resp.json()["pipeline_run_id"] == run_id


@pytest.mark.asyncio
async def test_get_report_includes_premissas_snapshot(
    auth_client: AsyncClient, tmp_path: Path, db: AsyncSession
):
    snap = {"schema": 1, "goals_json_sha256": "abc", "active_goals": []}
    rid = await _seed_report(
        auth_client,
        analysis_payload=None,
        premissas_snapshot_json=snap,
        tmp_path=tmp_path,
        db=db,
    )
    resp = await auth_client.get(f"/api/workspaces/{auth_client.ws_id}/reports/{rid}")
    assert resp.status_code == 200
    assert resp.json()["premissas_snapshot"] == snap


@pytest.mark.asyncio
async def test_list_reports_propagates_has_analysis_data(
    auth_client: AsyncClient, tmp_path: Path, db: AsyncSession
):
    (tmp_path / "a").mkdir(exist_ok=True)
    (tmp_path / "b").mkdir(exist_ok=True)
    await _seed_report(auth_client, analysis_payload={"x": 1}, tmp_path=tmp_path / "a", db=db)
    await _seed_report(auth_client, analysis_payload=None, tmp_path=tmp_path / "b", db=db)

    resp = await auth_client.get(f"/api/workspaces/{auth_client.ws_id}/reports")
    assert resp.status_code == 200
    flags = [r["has_analysis_data"] for r in resp.json()["reports"]]
    assert True in flags and False in flags


# ─── F0.4: GET /reports/{id}/data ──────────────────────────────────────


@pytest.mark.asyncio
async def test_get_report_data_unauthorized(client: AsyncClient):
    resp = await client.get(
        "/api/workspaces/00000000-0000-0000-0000-000000000000/reports/any-id/data"
    )
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_get_report_data_not_found(auth_client: AsyncClient):
    resp = await auth_client.get(f"/api/workspaces/{auth_client.ws_id}/reports/nonexistent-id/data")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_report_data_returns_json_payload(
    auth_client: AsyncClient, tmp_path: Path, db: AsyncSession
):
    payload = {
        "periodo_dados": "202601-202604",
        "patrimonio": {"bruto": 1234567.89, "liquido": 1200000.0},
        "score": {"valor": 85, "max": 100, "classificacao": "Muito Bom"},
    }
    rid = await _seed_report(auth_client, analysis_payload=payload, tmp_path=tmp_path, db=db)
    resp = await auth_client.get(f"/api/workspaces/{auth_client.ws_id}/reports/{rid}/data")
    assert resp.status_code == 200
    body = resp.json()
    assert body["periodo_dados"] == "202601-202604"
    assert body["patrimonio"]["bruto"] == 1234567.89
    assert body["score"]["classificacao"] == "Muito Bom"
    lin = body.get("_report_lineage")
    assert isinstance(lin, dict)
    assert "source_document_count" in lin
    assert "source_document_ids" in lin
    assert isinstance(lin["source_document_ids"], list)


@pytest.mark.asyncio
async def test_get_report_data_merges_premissas_snapshot_into_goals(
    auth_client: AsyncClient, tmp_path: Path, db: AsyncSession
):
    snap = {"schema": 1, "goals_json_sha256": "deadbeef", "active_goals": []}
    payload = {
        "periodo_dados": "202601-202604",
        "goals": {"if_pct": 42.0},
    }
    rid = await _seed_report(
        auth_client,
        analysis_payload=payload,
        premissas_snapshot_json=snap,
        tmp_path=tmp_path,
        db=db,
    )
    resp = await auth_client.get(f"/api/workspaces/{auth_client.ws_id}/reports/{rid}/data")
    assert resp.status_code == 200
    body = resp.json()
    assert body["goals"]["if_pct"] == 42.0
    assert body["goals"]["premissas_snapshot"] == snap


@pytest.mark.asyncio
async def test_get_report_data_404_when_analysis_missing(
    auth_client: AsyncClient, tmp_path: Path, db: AsyncSession
):
    """Relatório pré-F9 (sem analysis_json_path) retorna 404."""
    rid = await _seed_report(auth_client, analysis_payload=None, tmp_path=tmp_path, db=db)
    resp = await auth_client.get(f"/api/workspaces/{auth_client.ws_id}/reports/{rid}/data")
    assert resp.status_code == 404
    assert "análise" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_get_report_data_404_when_file_missing_from_disk(
    auth_client: AsyncClient, tmp_path: Path, db: AsyncSession
):
    """Path persistido mas arquivo apagado → 404 (não 500)."""
    rid = await _seed_report(auth_client, analysis_payload={"x": 1}, tmp_path=tmp_path, db=db)
    # Apaga o JSON do disco preservando a row do DB
    (tmp_path / "analysis.json").unlink()
    resp = await auth_client.get(f"/api/workspaces/{auth_client.ws_id}/reports/{rid}/data")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_report_data_500_when_json_corrupted(
    auth_client: AsyncClient, tmp_path: Path, db: AsyncSession
):
    rid = await _seed_report(auth_client, analysis_payload={"x": 1}, tmp_path=tmp_path, db=db)
    # Corrompe o arquivo
    (tmp_path / "analysis.json").write_text("{invalid json", encoding="utf-8")
    resp = await auth_client.get(f"/api/workspaces/{auth_client.ws_id}/reports/{rid}/data")
    assert resp.status_code == 500
    assert "corrompido" in resp.json()["detail"].lower()


# ─── F1.5: GET /reports/{id}/download.html ────────────────────────────


@pytest.mark.asyncio
async def test_download_html_unauthorized(client: AsyncClient):
    resp = await client.get(
        "/api/workspaces/00000000-0000-0000-0000-000000000000/reports/any-id/download.html"
    )
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_download_html_not_found(auth_client: AsyncClient):
    resp = await auth_client.get(
        f"/api/workspaces/{auth_client.ws_id}/reports/nonexistent-id/download.html"
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_download_html_sends_attachment_headers(
    auth_client: AsyncClient, tmp_path: Path, db: AsyncSession
):
    rid = await _seed_report(
        auth_client,
        html_content="<html><body>Relatório</body></html>",
        analysis_payload=None,
        tmp_path=tmp_path,
        db=db,
    )
    resp = await auth_client.get(f"/api/workspaces/{auth_client.ws_id}/reports/{rid}/download.html")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/html")
    disp = resp.headers["content-disposition"]
    assert disp.startswith("attachment;")
    assert "filename=" in disp
    assert b"Relat" in resp.content


@pytest.mark.asyncio
async def test_download_html_404_when_file_missing_from_disk(
    auth_client: AsyncClient, tmp_path: Path, db: AsyncSession
):
    rid = await _seed_report(auth_client, analysis_payload=None, tmp_path=tmp_path, db=db)
    (tmp_path / "report.html").unlink()
    resp = await auth_client.get(f"/api/workspaces/{auth_client.ws_id}/reports/{rid}/download.html")
    assert resp.status_code == 404


def test_download_html_sanitize_filename_helper():
    """Nome com caracteres perigosos deve virar whitelist antes do header."""
    from backend.app.api.reports import _sanitize_filename

    assert _sanitize_filename('abc"; rm -rf /') == "abc___rm_-rf"
    assert _sanitize_filename("relatório família.html") == "relat_rio_fam_lia.html"
    assert _sanitize_filename("") == "relatorio.html"
    assert _sanitize_filename("...") == "relatorio.html"
    assert _sanitize_filename("report_2026-04.html") == "report_2026-04.html"


@pytest.mark.asyncio
async def test_get_report_data_isolation_across_workspaces(
    auth_client: AsyncClient, client: AsyncClient, tmp_path: Path, db: AsyncSession
):
    """Garante scoping por workspace — user B não vê report de A."""
    # Cria o report no workspace do auth_client
    rid = await _seed_report(auth_client, analysis_payload={"x": 1}, tmp_path=tmp_path, db=db)
    # User B separado
    resp_b = await client.post(
        "/api/auth/register",
        json={
            "email": "user-b@test.com",
            "password": "testpass123",
            "full_name": "User B",
        },
    )
    token_b = resp_b.json()["access_token"]
    # Resolve B's own workspace id — B is now a legit tenant, just not the one
    # that holds the report (seeded under auth_client's workspace).
    from backend.app.models.user import User as _User
    from backend.app.models.workspace import Workspace as _Ws

    user_b = (await db.execute(select(_User).where(_User.email == "user-b@test.com"))).scalar_one()
    ws_b = (await db.execute(select(_Ws).where(_Ws.owner_id == user_b.id))).scalar_one()
    resp = await client.get(
        f"/api/workspaces/{ws_b.id}/reports/{rid}/data",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    # B autentica no próprio workspace mas o report vive no workspace do auth_client.
    # `get_current_workspace` passa (B é owner de ws_b), depois query retorna None (report não é de ws_b).
    assert resp.status_code == 404
