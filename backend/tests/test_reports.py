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
    await _seed_report(auth_client, analysis_payload={"x": 1}, tmp_path=tmp_path / "a")
    (tmp_path / "a").mkdir(exist_ok=True)
    await _seed_report(auth_client, analysis_payload=None, tmp_path=tmp_path / "b")
    (tmp_path / "b").mkdir(exist_ok=True)

    resp = await auth_client.get("/api/reports")
    assert resp.status_code == 200
    flags = [r["has_analysis_data"] for r in resp.json()["reports"]]
    assert True in flags and False in flags
