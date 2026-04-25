"""Tests for ``GET /reports/consumo-pontuais`` (defesa contra falha do E4)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from httpx import AsyncClient

from backend.app.application.report.consumo_pontuais import _resolve_period_dates
from backend.app.models.pipeline_artifact import PipelineArtifact
from backend.app.models.pipeline_run import PipelineRun, PipelineRunStatus


def test_resolve_period_dates_3m():
    today = datetime(2026, 4, 25, tzinfo=timezone.utc).date()
    date_from, date_to = _resolve_period_dates("3m", today=today)
    assert date_to == "2026-04-25"
    assert date_from < date_to


def test_resolve_period_dates_ytd():
    today = datetime(2026, 4, 25, tzinfo=timezone.utc).date()
    date_from, date_to = _resolve_period_dates("ytd", today=today)
    assert date_from == "2026-01-01"
    assert date_to == "2026-04-25"


def test_resolve_period_dates_invalid_raises():
    with pytest.raises(ValueError):
        _resolve_period_dates("1y")


def _despesa(descricao: str, qtd, *, categoria: str = "nao_identificado") -> dict:
    return {
        "data": datetime.now(timezone.utc).date().isoformat(),
        "descricao": descricao,
        "valor": qtd,
        "banco": "itau",
        "categoria": categoria,
    }


async def _seed_e4_despesas(db, workspace_id: str, despesas: list[dict]) -> None:
    """Seed E4 ``despesas`` artifact via ``db`` fixture (pytest-asyncio strict)."""
    run = PipelineRun(
        id=str(uuid4()), workspace_id=workspace_id, status=PipelineRunStatus.completed
    )
    db.add(run)
    await db.flush()
    payload_despesas = {"dados": {"nao_identificado": despesas}}
    db.add(_make_artifact(workspace_id, run.id, "despesas", payload_despesas))
    db.add(_make_artifact(workspace_id, run.id, "receitas", {"dados": {}}))
    await db.commit()


def _make_artifact(workspace_id: str, run_id: str, key: str, content: dict) -> PipelineArtifact:
    return PipelineArtifact(
        workspace_id=workspace_id,
        pipeline_run_id=run_id,
        stage="E4",
        artifact_key=key,
        content_json=content,
    )


def _seed_tenant_family_config(workspace_id: str) -> Path:
    """Materialize family_members.json + categorization.json mínimos no tenant."""
    from backend.app.core.config import settings

    tenant_config = Path(settings.STORAGE_ROOT) / workspace_id / "config"
    tenant_config.mkdir(parents=True, exist_ok=True)
    family = _family_config()
    (tenant_config / "family_members.json").write_text(json.dumps(family), encoding="utf-8")
    (tenant_config / "categorization.json").write_text(
        json.dumps({"internal_transfer_patterns": []}), encoding="utf-8"
    )
    return tenant_config


def _family_config() -> dict:
    return {
        "transferencias_internas": {
            "patterns_pix": [],
            "patterns_global": [],
            "patterns_bank_specific": {},
            "recipients": ["DAVID ROBERT CAMARGO", "MARIANA TEIXEIRA FERREIRA"],
        }
    }


@pytest.mark.asyncio
async def test_consumo_pontuais_excludes_internal_transfers_to_family(auth_client: AsyncClient, db):
    """Bug fix: PIX para nome da família não pode aparecer como gasto pontual."""
    despesas = [
        _despesa(
            "Pix enviado para DAVID ROBERT CAMARGO FERREIRA CAMPOS — TRANSF ENVIADA PIX C", 41000.0
        ),
        _despesa("RESTAURANTE FASANO", 5000.0),
    ]
    await _seed_e4_despesas(db, auth_client.ws_id, despesas)
    _seed_tenant_family_config(auth_client.ws_id)

    resp = await auth_client.get(
        f"/api/workspaces/{auth_client.ws_id}/reports/consumo-pontuais?period=3m"
    )
    assert resp.status_code == 200, resp.text
    descricoes = [it["descricao"] for it in resp.json()["items"]]
    assert any("FASANO" in d for d in descricoes)
    assert not any("DAVID ROBERT" in d for d in descricoes)


@pytest.mark.asyncio
async def test_consumo_pontuais_filters_below_threshold(auth_client: AsyncClient, db):
    despesas = [
        _despesa("PEQUENA COMPRA", 500.0, categoria="alimentacao"),
        _despesa("GRANDE COMPRA", 3500.0, categoria="alimentacao"),
    ]
    await _seed_e4_despesas(db, auth_client.ws_id, despesas)
    _seed_tenant_family_config(auth_client.ws_id)

    resp = await auth_client.get(
        f"/api/workspaces/{auth_client.ws_id}/reports/consumo-pontuais?period=3m"
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["descricao"] == "GRANDE COMPRA"


@pytest.mark.asyncio
async def test_consumo_pontuais_invalid_period(auth_client: AsyncClient):
    resp = await auth_client.get(
        f"/api/workspaces/{auth_client.ws_id}/reports/consumo-pontuais?period=1y"
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_consumo_pontuais_unauthorized(client: AsyncClient):
    resp = await client.get(
        "/api/workspaces/00000000-0000-0000-0000-000000000000/reports/consumo-pontuais?period=3m"
    )
    assert resp.status_code in (401, 403)
