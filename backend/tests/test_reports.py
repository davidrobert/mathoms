"""Tests for report endpoints — list, get, html, data (F9 · ADR-076)."""

import json
import uuid
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy import select


@pytest.mark.asyncio
async def test_list_reports_empty(auth_client: AsyncClient):
    resp = await auth_client.get("/api/reports")
    assert resp.status_code == 200
    data = resp.json()
    assert data["reports"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_list_reports_unauthorized(client: AsyncClient):
    resp = await client.get("/api/reports")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_get_report_not_found(auth_client: AsyncClient):
    resp = await auth_client.get("/api/reports/nonexistent-id")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_report_html_not_found(auth_client: AsyncClient):
    resp = await auth_client.get("/api/reports/nonexistent-id/html")
    assert resp.status_code == 404


# ─── F9 · ADR-076: analysis JSON endpoint ──────────────────────────────


async def _seed_report(
    auth_client: AsyncClient,
    *,
    html_content: str = "<html><body>ok</body></html>",
    analysis_payload: dict | None = None,
    tmp_path: Path,
) -> str:
    """Cria um Report vinculado ao workspace do auth_client e retorna seu id.

    Escreve HTML e (opcionalmente) o JSON de análise em `tmp_path` para que
    os endpoints possam servir os arquivos.
    """
    from backend.app.models.report import Report
    from backend.app.models.workspace import Workspace
    from backend.tests.conftest import TestSession

    html_file = tmp_path / "report.html"
    html_file.write_text(html_content, encoding="utf-8")

    analysis_path: Path | None = None
    if analysis_payload is not None:
        analysis_path = tmp_path / "analysis.json"
        analysis_path.write_text(json.dumps(analysis_payload), encoding="utf-8")

    async with TestSession() as session:
        ws = (await session.execute(select(Workspace))).scalar_one()
        report = Report(
            id=str(uuid.uuid4()),
            workspace_id=ws.id,
            pipeline_run_id=None,
            title="Relatório de Teste",
            html_path=str(html_file),
            analysis_json_path=str(analysis_path) if analysis_path else None,
            size_bytes=len(html_content),
        )
        session.add(report)
        await session.commit()
        return report.id


@pytest.mark.asyncio
async def test_get_report_includes_has_analysis_data_true(
    auth_client: AsyncClient, tmp_path: Path
):
    rid = await _seed_report(
        auth_client,
        analysis_payload={"periodo_dados": "202601-202604", "patrimonio": {}},
        tmp_path=tmp_path,
    )
    resp = await auth_client.get(f"/api/reports/{rid}")
    assert resp.status_code == 200
    assert resp.json()["has_analysis_data"] is True


@pytest.mark.asyncio
async def test_get_report_has_analysis_data_false_when_no_json(
    auth_client: AsyncClient, tmp_path: Path
):
    rid = await _seed_report(auth_client, analysis_payload=None, tmp_path=tmp_path)
    resp = await auth_client.get(f"/api/reports/{rid}")
    assert resp.status_code == 200
    assert resp.json()["has_analysis_data"] is False


@pytest.mark.asyncio
async def test_list_reports_propagates_has_analysis_data(
    auth_client: AsyncClient, tmp_path: Path
):
    (tmp_path / "a").mkdir(exist_ok=True)
    (tmp_path / "b").mkdir(exist_ok=True)
    await _seed_report(auth_client, analysis_payload={"x": 1}, tmp_path=tmp_path / "a")
    await _seed_report(auth_client, analysis_payload=None, tmp_path=tmp_path / "b")

    resp = await auth_client.get("/api/reports")
    assert resp.status_code == 200
    flags = [r["has_analysis_data"] for r in resp.json()["reports"]]
    assert True in flags and False in flags


# ─── F0.4: GET /reports/{id}/data ──────────────────────────────────────


@pytest.mark.asyncio
async def test_get_report_data_unauthorized(client: AsyncClient):
    resp = await client.get("/api/reports/any-id/data")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_get_report_data_not_found(auth_client: AsyncClient):
    resp = await auth_client.get("/api/reports/nonexistent-id/data")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_report_data_returns_json_payload(
    auth_client: AsyncClient, tmp_path: Path
):
    payload = {
        "periodo_dados": "202601-202604",
        "patrimonio": {"bruto": 1234567.89, "liquido": 1200000.0},
        "score": {"valor": 85, "max": 100, "classificacao": "Muito Bom"},
    }
    rid = await _seed_report(auth_client, analysis_payload=payload, tmp_path=tmp_path)
    resp = await auth_client.get(f"/api/reports/{rid}/data")
    assert resp.status_code == 200
    body = resp.json()
    assert body["periodo_dados"] == "202601-202604"
    assert body["patrimonio"]["bruto"] == 1234567.89
    assert body["score"]["classificacao"] == "Muito Bom"


@pytest.mark.asyncio
async def test_get_report_data_404_when_analysis_missing(
    auth_client: AsyncClient, tmp_path: Path
):
    """Relatório pré-F9 (sem analysis_json_path) retorna 404."""
    rid = await _seed_report(auth_client, analysis_payload=None, tmp_path=tmp_path)
    resp = await auth_client.get(f"/api/reports/{rid}/data")
    assert resp.status_code == 404
    assert "análise" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_get_report_data_404_when_file_missing_from_disk(
    auth_client: AsyncClient, tmp_path: Path
):
    """Path persistido mas arquivo apagado → 404 (não 500)."""
    rid = await _seed_report(
        auth_client, analysis_payload={"x": 1}, tmp_path=tmp_path
    )
    # Apaga o JSON do disco preservando a row do DB
    (tmp_path / "analysis.json").unlink()
    resp = await auth_client.get(f"/api/reports/{rid}/data")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_report_data_500_when_json_corrupted(
    auth_client: AsyncClient, tmp_path: Path
):
    rid = await _seed_report(
        auth_client, analysis_payload={"x": 1}, tmp_path=tmp_path
    )
    # Corrompe o arquivo
    (tmp_path / "analysis.json").write_text("{invalid json", encoding="utf-8")
    resp = await auth_client.get(f"/api/reports/{rid}/data")
    assert resp.status_code == 500
    assert "corrompido" in resp.json()["detail"].lower()


# ─── F1.5: GET /reports/{id}/download.html ────────────────────────────


@pytest.mark.asyncio
async def test_download_html_unauthorized(client: AsyncClient):
    resp = await client.get("/api/reports/any-id/download.html")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_download_html_not_found(auth_client: AsyncClient):
    resp = await auth_client.get("/api/reports/nonexistent-id/download.html")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_download_html_sends_attachment_headers(
    auth_client: AsyncClient, tmp_path: Path
):
    rid = await _seed_report(
        auth_client,
        html_content="<html><body>Relatório</body></html>",
        analysis_payload=None,
        tmp_path=tmp_path,
    )
    resp = await auth_client.get(f"/api/reports/{rid}/download.html")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/html")
    disp = resp.headers["content-disposition"]
    assert disp.startswith("attachment;")
    assert "filename=" in disp
    assert b"Relat" in resp.content


@pytest.mark.asyncio
async def test_download_html_404_when_file_missing_from_disk(
    auth_client: AsyncClient, tmp_path: Path
):
    rid = await _seed_report(auth_client, analysis_payload=None, tmp_path=tmp_path)
    (tmp_path / "report.html").unlink()
    resp = await auth_client.get(f"/api/reports/{rid}/download.html")
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
    auth_client: AsyncClient, client: AsyncClient, tmp_path: Path
):
    """Garante scoping por workspace — user B não vê report de A."""
    # Cria o report no workspace do auth_client
    rid = await _seed_report(
        auth_client, analysis_payload={"x": 1}, tmp_path=tmp_path
    )
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
    resp = await client.get(
        f"/api/reports/{rid}/data",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp.status_code == 404
