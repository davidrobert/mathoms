"""Tests for TransferConfig (ADR-133) — model, repo, endpoint, materializer overlay."""

from __future__ import annotations

import json

import pytest
from httpx import AsyncClient

from backend.app.models.config_blob import TransferConfig
from backend.app.repositories.config_blob_repository import ConfigBlobRepository


def _payload() -> dict:
    return {
        "patterns_pix": ["PIX TRANSF DAVID"],
        "patterns_global": ["TED D HBANK"],
        "patterns_bank_specific": {"c6bank": ["Pagamento"]},
        "recipients": ["DAVID ROBERT", "MARIANA TEIXEIRA"],
    }


@pytest.mark.asyncio
async def test_get_transfer_config_falls_back_to_global(auth_client: AsyncClient):
    """Sem row no DB → endpoint retorna o bloco do global config."""
    resp = await auth_client.get(f"/api/workspaces/{auth_client.ws_id}/config/transfer")
    assert resp.status_code == 200
    data = resp.json()
    assert "recipients" in data and isinstance(data["recipients"], list)


@pytest.mark.asyncio
async def test_put_transfer_config_persists(auth_client: AsyncClient):
    body = _payload()
    resp = await auth_client.put(f"/api/workspaces/{auth_client.ws_id}/config/transfer", json=body)
    assert resp.status_code == 200, resp.text
    saved = resp.json()
    assert saved["recipients"] == ["DAVID ROBERT", "MARIANA TEIXEIRA"]
    assert saved["patterns_bank_specific"] == {"c6bank": ["Pagamento"]}

    resp = await auth_client.get(f"/api/workspaces/{auth_client.ws_id}/config/transfer")
    assert resp.json()["patterns_pix"] == ["PIX TRANSF DAVID"]


@pytest.mark.asyncio
async def test_repo_get_returns_none_when_absent(auth_client: AsyncClient, db):
    repo = ConfigBlobRepository(db)
    assert await repo.get_config_json(auth_client.ws_id, TransferConfig) is None


@pytest.mark.asyncio
async def test_repo_upsert_creates_then_replaces(auth_client: AsyncClient, db):
    repo = ConfigBlobRepository(db)
    payload = _payload()
    cfg = await repo.upsert(auth_client.ws_id, TransferConfig, payload)
    assert cfg.config_json["recipients"] == payload["recipients"]
    payload["recipients"] = ["NEW NAME"]
    await repo.upsert(auth_client.ws_id, TransferConfig, payload)
    result = await repo.get_config_json(auth_client.ws_id, TransferConfig)
    assert result is not None and result["recipients"] == ["NEW NAME"]


def _custom_config(recipients: list[str]) -> dict:
    return {
        "patterns_pix": [],
        "patterns_global": [],
        "patterns_bank_specific": {},
        "recipients": recipients,
    }


def _despesa(descricao: str, qtd: float) -> dict:
    from datetime import datetime, timezone

    return {
        "data": datetime.now(timezone.utc).date().isoformat(),
        "descricao": descricao,
        "valor": qtd,
        "banco": "itau",
        "categoria": "nao_identificado",
    }


async def _seed_e4(db, workspace_id: str, despesas: list[dict]) -> None:
    from uuid import uuid4

    from backend.app.models.pipeline_artifact import PipelineArtifact
    from backend.app.models.pipeline_run import PipelineRun, PipelineRunStatus

    run = PipelineRun(
        id=str(uuid4()), workspace_id=workspace_id, status=PipelineRunStatus.completed
    )
    db.add(run)
    await db.flush()
    db.add(_artifact(workspace_id, run.id, "despesas", {"dados": {"nao_identificado": despesas}}))
    db.add(_artifact(workspace_id, run.id, "receitas", {"dados": {}}))
    await db.commit()


def _artifact(workspace_id: str, run_id: str, key: str, content: dict):
    from backend.app.models.pipeline_artifact import PipelineArtifact

    return PipelineArtifact(
        workspace_id=workspace_id,
        pipeline_run_id=run_id,
        stage="E4",
        artifact_key=key,
        content_json=content,
    )


async def _put_recipients(auth_client: AsyncClient, recipients: list[str]) -> None:
    resp = await auth_client.put(
        f"/api/workspaces/{auth_client.ws_id}/config/transfer",
        json=_custom_config(recipients),
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_consumo_pontuais_uses_db_recipient(auth_client: AsyncClient, db, tmp_path):
    """End-to-end: persiste recipient no DB e confirma que /consumo-pontuais o usa."""
    await _put_recipients(auth_client, ["FULANO CUSTOM"])
    despesas = [
        _despesa("Pix enviado para FULANO CUSTOM", 5000.0),
        _despesa("RESTAURANTE FASANO", 5000.0),
    ]
    await _seed_e4(db, auth_client.ws_id, despesas)
    resp = await auth_client.get(
        f"/api/workspaces/{auth_client.ws_id}/reports/consumo-pontuais?period=3m"
    )
    assert resp.status_code == 200
    descricoes = [it["descricao"] for it in resp.json()["items"]]
    assert any("FASANO" in d for d in descricoes)
    assert not any("FULANO CUSTOM" in d for d in descricoes)


# A7.5 (ADR-134): ``_override_transfer_config`` foi removido — bloco
# ``transferencias_internas`` flui via ``WorkspaceContext.config_overrides``
# (build_config_overrides_from_db._family_members_override funde DB +
# transferencias_internas em memória, sem materializar em disco).
# Test de overlay-em-disco descontinuado nesta sprint.
