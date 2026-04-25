"""Tests for report endpoints — list, get, data, pdf (F9 · ADR-076 · ADR-129 · ADR-131)."""

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


# ─── F9 · ADR-076 · ADR-129: analysis JSON endpoint ────────────────────


async def _seed_report(
    auth_client: AsyncClient,
    *,
    analysis_payload: dict | None = None,
    pipeline_run_id: str | None = None,
    premissas_snapshot_json: dict | None = None,
    tmp_path: Path,
    db: AsyncSession | None = None,
) -> str:
    """Cria um Report vinculado ao workspace do auth_client e retorna seu id.

    ADR-131: quando ``analysis_payload`` é dado, cria um ``PipelineArtifact``
    no DB com aquele conteúdo e referencia via ``analysis_artifact_id``.
    Quando ``None``, deixa a FK como NULL (relatório sem análise — pré-F9
    ou cujo run foi hard-deleted).

    ``db`` — deve ser a fixture ``db`` do conftest. Usar TestSession()
    direto causa "no such table" em pytest-asyncio strict mode porque a
    session é criada fora do lifecycle de fixtures.
    """
    from backend.app.models.pipeline_artifact import PipelineArtifact
    from backend.app.models.pipeline_run import PipelineRun, PipelineRunStatus
    from backend.app.models.report import Report
    from backend.app.models.workspace import Workspace

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

        artifact_id: int | None = None
        if analysis_payload is not None:
            # PipelineArtifact requer pipeline_run_id (FK NOT NULL); cria
            # um run sintético quando o caller não passou.
            run_id = pipeline_run_id or str(uuid.uuid4())
            existing_run = (
                await session.execute(select(PipelineRun).where(PipelineRun.id == run_id))
            ).scalar_one_or_none()
            if existing_run is None:
                session.add(
                    PipelineRun(
                        id=run_id,
                        workspace_id=ws.id,
                        status=PipelineRunStatus.completed,
                    )
                )
                await session.flush()
                pipeline_run_id = run_id
            artifact = PipelineArtifact(
                workspace_id=ws.id,
                pipeline_run_id=run_id,
                stage="E5",
                artifact_key="analise_financeira",
                content_json=analysis_payload,
            )
            session.add(artifact)
            await session.flush()
            artifact_id = artifact.id

        report = Report(
            id=str(uuid.uuid4()),
            workspace_id=ws.id,
            pipeline_run_id=pipeline_run_id,
            title="Relatório de Teste",
            analysis_artifact_id=artifact_id,
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
    assert "consumed_document_count" in data
    assert "consumed_document_ids" in data
    assert isinstance(data["consumed_document_ids"], list)


def _make_doc(ws_id: str, name: str):
    from backend.app.models.document import Document, DocumentStatus, DocumentType

    return Document(
        id=str(uuid.uuid4()),
        workspace_id=ws_id,
        original_name=name,
        doc_type=DocumentType.bank_statement,
        status=DocumentStatus.processed,
    )


def _make_artifact(ws_id: str, run_id: str, stage: str, key: str, doc_id: str | None):
    from backend.app.models.pipeline_artifact import PipelineArtifact

    return PipelineArtifact(
        workspace_id=ws_id,
        pipeline_run_id=run_id,
        stage=stage,
        artifact_key=key,
        document_id=doc_id,
        content_json={},
    )


async def _seed_extraction_artifacts(
    db: AsyncSession, ws_id: str, run_id: str, n_docs: int
) -> list[str]:
    docs = [_make_doc(ws_id, f"{i}.pdf") for i in range(n_docs)]
    db.add_all(docs)
    await db.flush()
    artifacts = [
        _make_artifact(ws_id, run_id, "extract_statements", f"{d.original_name}-2_extract", d.id)
        for d in docs
    ]
    artifacts.append(_make_artifact(ws_id, run_id, "reconcile_transactions", "recon", None))
    db.add_all(artifacts)
    await db.commit()
    return [d.id for d in docs]


@pytest.mark.asyncio
async def test_get_report_consumed_document_count_reflects_extraction_artifacts(
    auth_client: AsyncClient, tmp_path: Path, db: AsyncSession
):
    from backend.app.models.workspace import Workspace

    run_id = str(uuid.uuid4())
    rid = await _seed_report(
        auth_client, analysis_payload={"x": 1}, pipeline_run_id=run_id, tmp_path=tmp_path, db=db
    )
    ws = (await db.execute(select(Workspace))).scalar_one()
    doc_ids = await _seed_extraction_artifacts(db, ws.id, run_id, n_docs=2)

    resp = await auth_client.get(f"/api/workspaces/{auth_client.ws_id}/reports/{rid}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["consumed_document_count"] == 2
    assert set(data["consumed_document_ids"]) == set(doc_ids)


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
    """Relatório pré-F9 ou cujo run/artifact foi removido (analysis_artifact_id NULL) → 404."""
    rid = await _seed_report(auth_client, analysis_payload=None, tmp_path=tmp_path, db=db)
    resp = await auth_client.get(f"/api/workspaces/{auth_client.ws_id}/reports/{rid}/data")
    assert resp.status_code == 404
    assert "análise" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_get_report_data_404_after_artifact_deleted(
    auth_client: AsyncClient, tmp_path: Path, db: AsyncSession
):
    """ADR-131: artifact removido (ON DELETE SET NULL) → 404, não 500."""
    from backend.app.models.pipeline_artifact import PipelineArtifact
    from backend.app.models.report import Report

    rid = await _seed_report(auth_client, analysis_payload={"x": 1}, tmp_path=tmp_path, db=db)
    # Carrega o report para obter analysis_artifact_id, apaga o artifact
    # (FK ON DELETE SET NULL preserva a row do Report).
    report = (await db.execute(select(Report).where(Report.id == rid))).scalar_one()
    assert report.analysis_artifact_id is not None
    artifact = (
        await db.execute(
            select(PipelineArtifact).where(PipelineArtifact.id == report.analysis_artifact_id)
        )
    ).scalar_one()
    await db.delete(artifact)
    await db.commit()

    resp = await auth_client.get(f"/api/workspaces/{auth_client.ws_id}/reports/{rid}/data")
    assert resp.status_code == 404


# ─── ADR-129: sanitize helper segue em uso pelo download PDF ───────────


def test_sanitize_filename_helper():
    from backend.app.api.reports import _sanitize_filename

    assert _sanitize_filename('abc"; rm -rf /') == "abc___rm_-rf"
    assert _sanitize_filename("relatório família.pdf") == "relat_rio_fam_lia.pdf"
    assert _sanitize_filename("") == "relatorio.pdf"
    assert _sanitize_filename("...") == "relatorio.pdf"
    assert _sanitize_filename("report_2026-04.pdf") == "report_2026-04.pdf"


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
