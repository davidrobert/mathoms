"""Tests for ``GET /reports/consumo-pontuais`` — gastos pontuais ≥ R$2k.

Cobre o fix do bug onde transferências PIX entre contas da família apareciam
no card "Consumo Consciente" como saídas (E4 deixava cair em
``nao_identificado``; o filtro do frontend não tinha rede de proteção).
A lógica agora vive no backend e aplica ``InternalTransferDetector`` como
defesa em profundidade contra falhas do E4.
"""

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


async def _seed_e4_despesas(db, workspace_id: str, despesas: list[dict]) -> None:
    """Seed E4 despesas artifact directly via the test ``db`` fixture session.

    Usar a fixture ``db`` (e não ``TestSession()`` direto) garante que as
    inserções caem no mesmo ciclo de vida que cria/dropa as tabelas em
    pytest-asyncio strict mode.
    """
    run = PipelineRun(
        id=str(uuid4()),
        workspace_id=workspace_id,
        status=PipelineRunStatus.completed,
    )
    db.add(run)
    await db.flush()
    db.add(
        PipelineArtifact(
            workspace_id=workspace_id,
            pipeline_run_id=run.id,
            stage="E4",
            artifact_key="despesas",
            content_json={"dados": {"nao_identificado": despesas}},
        )
    )
    db.add(
        PipelineArtifact(
            workspace_id=workspace_id,
            pipeline_run_id=run.id,
            stage="E4",
            artifact_key="receitas",
            content_json={"dados": {}},
        )
    )
    await db.commit()


def _seed_tenant_family_config(workspace_id: str) -> Path:
    """Materialize a minimal family_members.json + categorization.json for the tenant."""
    from backend.app.core.config import settings

    tenant_config = Path(settings.STORAGE_ROOT) / workspace_id / "config"
    tenant_config.mkdir(parents=True, exist_ok=True)
    family = {
        "transferencias_internas": {
            "patterns_pix": [],
            "patterns_global": [],
            "patterns_bank_specific": {},
            "recipients": [
                "DAVID ROBERT CAMARGO",
                "MARIANA TEIXEIRA FERREIRA",
            ],
        }
    }
    categorization = {"internal_transfer_patterns": []}
    (tenant_config / "family_members.json").write_text(
        json.dumps(family, ensure_ascii=False), encoding="utf-8"
    )
    (tenant_config / "categorization.json").write_text(
        json.dumps(categorization, ensure_ascii=False), encoding="utf-8"
    )
    return tenant_config


@pytest.mark.asyncio
async def test_consumo_pontuais_excludes_internal_transfers_to_family(
    auth_client: AsyncClient, db
):
    """Bug fix: PIX para nome da família não pode aparecer como gasto pontual."""
    today = datetime.now(timezone.utc).date().isoformat()
    despesas = [
        {
            "data": today,
            "descricao": "Pix enviado para DAVID ROBERT CAMARGO FERREIRA CAMPOS — TRANSF ENVIADA PIX C",
            "valor": 41000.0,
            "banco": "itau",
            "categoria": "nao_identificado",
        },
        {
            "data": today,
            "descricao": "RESTAURANTE FASANO",
            "valor": 5000.0,
            "banco": "c6bank",
            "categoria": "nao_identificado",
        },
    ]
    await _seed_e4_despesas(db, auth_client.ws_id, despesas)
    _seed_tenant_family_config(auth_client.ws_id)

    resp = await auth_client.get(
        f"/api/workspaces/{auth_client.ws_id}/reports/consumo-pontuais?period=3m"
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    descricoes = [it["descricao"] for it in data["items"]]
    assert any("FASANO" in d for d in descricoes), data
    assert not any("DAVID ROBERT" in d for d in descricoes), data
    assert data["total"] == 1


@pytest.mark.asyncio
async def test_consumo_pontuais_filters_below_threshold(auth_client: AsyncClient, db):
    today = datetime.now(timezone.utc).date().isoformat()
    despesas = [
        {
            "data": today,
            "descricao": "PEQUENA COMPRA",
            "valor": 500.0,
            "banco": "itau",
            "categoria": "alimentacao",
        },
        {
            "data": today,
            "descricao": "GRANDE COMPRA",
            "valor": 3500.0,
            "banco": "itau",
            "categoria": "alimentacao",
        },
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
