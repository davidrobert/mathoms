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
    db: AsyncSession, ws_id: str, run_id: str, keys: list[str]
) -> None:
    """Adiciona artefatos E2 (stage extract_statements) + 1 não-extract (deve ser ignorado)."""
    artifacts = [_make_artifact(ws_id, run_id, "extract_statements", k, doc_id=None) for k in keys]
    artifacts.append(_make_artifact(ws_id, run_id, "reconcile_transactions", "recon", None))
    db.add_all(artifacts)
    await db.commit()


@pytest.mark.asyncio
async def test_get_report_consumed_document_count_reflects_extraction_artifacts(
    auth_client: AsyncClient, tmp_path: Path, db: AsyncSession
):
    """Conta DISTINCT artifact_key em stages E2; ignora outros stages e document_id=NULL."""
    from backend.app.models.workspace import Workspace

    run_id = str(uuid.uuid4())
    rid = await _seed_report(
        auth_client, analysis_payload={"x": 1}, pipeline_run_id=run_id, tmp_path=tmp_path, db=db
    )
    ws = (await db.execute(select(Workspace))).scalar_one()
    keys = ["a-2_extract", "b-2_extract"]
    await _seed_extraction_artifacts(db, ws.id, run_id, keys)

    resp = await auth_client.get(f"/api/workspaces/{auth_client.ws_id}/reports/{rid}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["consumed_document_count"] == 2
    assert set(data["consumed_document_ids"]) == set(keys)


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
async def test_get_report_includes_workspace_family_surname_when_set(
    auth_client: AsyncClient, tmp_path: Path, db: AsyncSession
):
    """v2.F.3a — surname populado a partir de Workspace.family_surname."""
    from backend.app.models.workspace import Workspace

    rid = await _seed_report(auth_client, analysis_payload=None, tmp_path=tmp_path, db=db)
    ws = (await db.execute(select(Workspace))).scalar_one()
    ws.family_surname = "Silva"
    await db.commit()

    resp = await auth_client.get(f"/api/workspaces/{auth_client.ws_id}/reports/{rid}")
    assert resp.status_code == 200
    assert resp.json()["workspace_family_surname"] == "Silva"


@pytest.mark.asyncio
async def test_get_report_workspace_family_surname_none_when_unset(
    auth_client: AsyncClient, tmp_path: Path, db: AsyncSession
):
    """v2.F.3a — sem surname devolve None (não 4xx/5xx)."""
    rid = await _seed_report(auth_client, analysis_payload=None, tmp_path=tmp_path, db=db)
    resp = await auth_client.get(f"/api/workspaces/{auth_client.ws_id}/reports/{rid}")
    assert resp.status_code == 200
    assert resp.json()["workspace_family_surname"] is None


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
async def test_get_report_data_decrypts_encrypted_artifact_payload(
    auth_client: AsyncClient, tmp_path: Path, db: AsyncSession
):
    """Regressão ADR-231/PR #359 — artifact criptografado via ORM/SQL fora do DBArtifactStore deve devolver plaintext (não o envelope Fernet)."""
    from backend.app.services.security.crypto import encrypt_artifact_payload

    plain = {
        "periodo_dados": "202601-202604",
        "patrimonio": {"bruto": 1234567.89, "liquido": 1200000.0},
        "score": {"valor": 85, "max": 100, "classificacao": "Muito Bom"},
    }
    sentinel = encrypt_artifact_payload(plain)
    assert sentinel.get("_encrypted") is True
    assert "ct" in sentinel

    rid = await _seed_report(auth_client, analysis_payload=sentinel, tmp_path=tmp_path, db=db)
    resp = await auth_client.get(f"/api/workspaces/{auth_client.ws_id}/reports/{rid}/data")
    assert resp.status_code == 200
    body = resp.json()
    assert "_encrypted" not in body
    assert "ct" not in body
    assert body["periodo_dados"] == "202601-202604"
    assert body["patrimonio"]["bruto"] == 1234567.89
    assert body["score"]["classificacao"] == "Muito Bom"


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


# ─── v2.8 (ADR-148): comparisons + changelog no payload ───────────────


@pytest.mark.asyncio
async def test_get_report_data_comparisons_null_when_first_report(
    auth_client: AsyncClient, tmp_path: Path, db: AsyncSession
):
    """Primeiro relatório do workspace ⇒ ``comparisons: null, changelog: null`` (D3)."""
    payload = {
        "periodo_dados": "202601-202604",
        "patrimonio": {"liquido": 1_000_000.0, "bruto": 1_200_000.0},
        "fluxo_caixa": {
            "receita_total": 50_000.0,
            "despesa_total": 30_000.0,
            "investimentos_total": 10_000.0,
        },
    }
    rid = await _seed_report(auth_client, analysis_payload=payload, tmp_path=tmp_path, db=db)
    resp = await auth_client.get(f"/api/workspaces/{auth_client.ws_id}/reports/{rid}/data")
    assert resp.status_code == 200
    body = resp.json()
    assert body["comparisons"] is None
    assert body["changelog"] is None


@pytest.mark.asyncio
async def test_get_report_data_comparisons_present_with_previous_snapshot(
    auth_client: AsyncClient, tmp_path: Path, db: AsyncSession
):
    """Segundo relatório ⇒ ``comparisons``/``changelog``/``comparison_periods``
    populados com as métricas canônicas v3 (ADR-190 §Emenda 2026-07-09)."""
    # Seed prev primeiro (created_at < curr).
    await _seed_report(auth_client, analysis_payload=_PREV_CANONICAL, tmp_path=tmp_path, db=db)
    rid_curr = await _seed_report(
        auth_client, analysis_payload=_CURR_CANONICAL, tmp_path=tmp_path, db=db
    )

    resp = await auth_client.get(f"/api/workspaces/{auth_client.ws_id}/reports/{rid_curr}/data")
    assert resp.status_code == 200
    body = resp.json()
    _assert_canonical_comparisons(body["comparisons"])
    # Moldura temporal real do par (copy da V0) + changelog só não-stable.
    assert body["comparison_periods"] == {"current": "202604", "previous": "202603"}
    assert len(body["changelog"]) >= 1
    assert [e for e in body["changelog"] if e["section_id"] == "M_RESERVA_MESES"] == []


_PREV_CANONICAL = {
    "periodo_dados": "202601-202603",
    "patrimonio": {"liquido": 1_000_000.0, "bruto": 1_200_000.0},
    "ratios": {"taxa_poupanca_recorrente_pct": 20.0},
    "reserva": {"cobertura_meses": 6.0},
    "goals": {"alocacao_alvo": {"derived": {"desvio_max_pct": 4.0}}},
}
_CURR_CANONICAL = {
    "periodo_dados": "202602-202604",
    "patrimonio": {"liquido": 1_100_000.0, "bruto": 1_300_000.0},
    "ratios": {"taxa_poupanca_recorrente_pct": 26.0},
    "reserva": {"cobertura_meses": 6.2},
    "goals": {"alocacao_alvo": {"derived": {"desvio_max_pct": 9.0}}},
}


def _assert_canonical_comparisons(items: list) -> None:
    """Contrato v3 no wire: ids canônicos, unit por métrica, thresholds absolutos."""
    assert isinstance(items, list)
    section_ids = [it["section_id"] for it in items]
    assert section_ids == ["M_PL", "M_TAXA_POUPANCA", "M_RESERVA_MESES", "M_AUVP_DESVIO"]
    by_id = {it["section_id"]: it for it in items}
    _assert_pl_item(by_id["M_PL"])
    # W2 (ADR-190 D3) + thresholds absolutos na unidade própria.
    expected = {
        "M_AUVP_DESVIO": ("pp", "up", "down"),
        "M_TAXA_POUPANCA": ("pp", "up", "up"),
        "M_RESERVA_MESES": ("meses", "stable", "up"),
    }
    for sid, (unit, signal, direction) in expected.items():
        item = by_id[sid]
        assert (item["unit"], item["delta_signal"], item["direction_positive"]) == (
            unit,
            signal,
            direction,
        )


def _assert_pl_item(pl: dict) -> None:
    assert pl["before"] == pytest.approx(1_000_000.0)
    assert pl["after"] == pytest.approx(1_100_000.0)
    assert (pl["delta_signal"], pl["unit"], pl["direction_positive"]) == ("up", "brl", "up")
    assert pl["delta_pct"] == pytest.approx(10.0, rel=1e-3)


# ─── ADR-129: sanitize helper segue em uso pelo download PDF ───────────


def test_sanitize_filename_helper():
    from backend.app.api.reports import _sanitize_filename

    assert _sanitize_filename('abc"; rm -rf /') == "abc___rm_-rf"
    assert _sanitize_filename("relatório família.pdf") == "relat_rio_fam_lia.pdf"
    assert _sanitize_filename("") == "relatorio.pdf"
    assert _sanitize_filename("...") == "relatorio.pdf"
    assert _sanitize_filename("report_2026-04.pdf") == "report_2026-04.pdf"


# ─── v2.F.3c: PDF filename composition (família + período) ─────────────


def test_pdf_filename_with_family_and_period():
    from datetime import datetime, timezone

    from backend.app.application.report._common import compose_pdf_filename

    name = compose_pdf_filename(
        "Andrade Silva",
        "2023-01 a 2026-04",
        datetime(2026, 4, 26, tzinfo=timezone.utc),
    )
    assert name == "mathoms-planejamento-andrade-silva-2026-04.pdf"


def test_pdf_filename_without_family_uses_period_only():
    from datetime import datetime, timezone

    from backend.app.application.report._common import compose_pdf_filename

    name = compose_pdf_filename(
        None, "2023-01 a 2026-04", datetime(2026, 4, 26, tzinfo=timezone.utc)
    )
    assert name == "mathoms-planejamento-2026-04.pdf"

    name_empty = compose_pdf_filename(
        "   ", "2023-01 a 2026-04", datetime(2026, 4, 26, tzinfo=timezone.utc)
    )
    assert name_empty == "mathoms-planejamento-2026-04.pdf"


def test_pdf_filename_without_period_falls_back_to_generated_at():
    from datetime import datetime, timezone

    from backend.app.application.report._common import compose_pdf_filename

    generated = datetime(2026, 4, 26, 12, 30, tzinfo=timezone.utc)
    name = compose_pdf_filename("Silva", None, generated)
    assert name == "mathoms-planejamento-silva-2026-04.pdf"

    name_blank = compose_pdf_filename("Silva", "", generated)
    assert name_blank == "mathoms-planejamento-silva-2026-04.pdf"


def test_pdf_filename_slug_strips_accents_and_spaces():
    from datetime import datetime, timezone

    from backend.app.application.report._common import (
        compose_pdf_filename,
        slugify_family,
    )

    assert slugify_family("Andrade Silva") == "andrade-silva"
    assert slugify_family("Gonçalves d'Ávila") == "goncalves-d-avila"
    assert slugify_family("  ÁCEnts   ") == "acents"

    name = compose_pdf_filename(
        "Gonçalves d'Ávila",
        "2023-01 a 2026-04",
        datetime(2026, 4, 26, tzinfo=timezone.utc),
    )
    assert name == "mathoms-planejamento-goncalves-d-avila-2026-04.pdf"


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
