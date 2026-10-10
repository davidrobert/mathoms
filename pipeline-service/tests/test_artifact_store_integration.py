"""Integração ADR-303: stage real via HTTP persiste em ``pipeline_artifacts``.

O gate que faltava — o baseline A2 media só ``/health``, que não toca o
store, e o modo HTTP quebrou em silêncio quando ADR-212 exigiu injeção
explícita. Este teste exercita ``reconcile_transactions`` de ponta a ponta:
seed E2 no DB → POST HTTP → assert row E3 no DB.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_E2_FIXTURE = (
    _REPO_ROOT / "tests" / "fixtures" / "pipeline_golden" / "e2" / "minimal-extrato-2_extract.json"
)


@pytest.fixture
def tenant_minimal(tmp_path: Path) -> Path:
    """Workspace com config mínima (espelho de tests/test_e3_golden_execution.py)."""
    cfg = tmp_path / "config"
    cfg.mkdir(parents=True)
    (cfg / "pipeline.json").write_text(
        '{"reconciliation": {"skip_types": [], "skip_files": []}}',
        encoding="utf-8",
    )
    (cfg / "family_members.json").write_text("{}", encoding="utf-8")
    (cfg / "institutions.json").write_text('{"banco_canonical": {}}', encoding="utf-8")
    return tmp_path


@pytest.fixture
def _plaintext_artifacts(monkeypatch):
    """Desliga crypto de artefatos — caminho Fernet é coberto por
    ``backend/tests/test_crypto_artifact.py``; aqui o alvo é o boundary."""
    from backend.app.core.config import settings

    monkeypatch.setattr(settings, "ENCRYPT_PIPELINE_ARTIFACTS", False)


def _seed_e2(factory, workspace_id: str, run_id: str) -> None:
    from backend.app.services.storage.db_artifact_store import DBArtifactStore

    payload = json.loads(_E2_FIXTURE.read_text(encoding="utf-8"))
    payload["saldo_inicial"] = 0.0
    payload["saldo_final"] = 100.0

    session = factory()
    try:
        store = DBArtifactStore(session, workspace_id=workspace_id, pipeline_run_id=run_id)
        store.write("E2-extratos", "golden-minimal", payload)
        session.commit()
    finally:
        session.close()


def test_reconcile_via_http_persists_e3_artifact(
    client, tenant_minimal, artifact_db_session_factory, _plaintext_artifacts
):
    from backend.app.services.storage.db_artifact_store import DBArtifactStore

    _seed_e2(artifact_db_session_factory, "ws-int", "run-int")

    r = client.post(
        "/api/v1/pipeline/stages/reconcile_transactions/execute",
        json={
            "run_id": "run-int",
            "workspace_id": "ws-int",
            "workspace_root": str(tenant_minimal),
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["success"] is True, body
    assert body["stage"] == "reconcile_transactions"

    session = artifact_db_session_factory()
    try:
        store = DBArtifactStore(session, workspace_id="ws-int", pipeline_run_id="run-int")
        e3_keys = store.list_keys("E3")
        assert len(e3_keys) == 1, f"expected one E3 key, got {e3_keys}"
        persisted = store.read("E3", e3_keys[0])
    finally:
        session.close()

    assert persisted is not None
    assert persisted["banco"] == "itau"
    assert persisted["transacoes_total"] == 1
    assert persisted["transacoes"][0]["valor"] == 100.0


# ADR-291 · ADR-303 D2, ponta a ponta: o `HttpPipelineClient` do backend contra o
# app real. O MockTransport do backend prova o que vai no fio; aqui o E4 real tem
# que achar, pelo pin, o E3 que o reconcile real gravou no run base.
def _seed_base_run_e3(client, factory, tenant: Path) -> None:
    _seed_e2(factory, "ws-int", "run-base")
    r = client.post(
        "/api/v1/pipeline/stages/reconcile_transactions/execute",
        json={"run_id": "run-base", "workspace_id": "ws-int", "workspace_root": str(tenant)},
    )
    assert r.status_code == 200 and r.json()["success"] is True, r.text


def _categorize_tail_via_backend_client(client, tenant: Path, *, pinned: bool):
    from backend.app.services.pipeline.pipeline_client import HttpPipelineClient
    from pipeline.context import WorkspaceContext

    ctx = WorkspaceContext.for_tenant(tenant, pipeline_run_id="run-cauda")
    ctx.llm_calls_allowed = False
    if pinned:
        ctx.base_run_id = "run-base"
        ctx.base_run_fallback_stages = frozenset({"E3", "reconcile_transactions"})
    backend_client = HttpPipelineClient(str(client.base_url), http=client)
    return backend_client.execute_stage(ctx, "categorize_transactions", workspace_id="ws-int")


def _tail_e4_receitas(factory) -> dict | None:
    from backend.app.services.storage.db_artifact_store import DBArtifactStore

    session = factory()
    try:
        store = DBArtifactStore(session, workspace_id="ws-int", pipeline_run_id="run-cauda")
        return store.read("categorize_transactions", "receitas")
    finally:
        session.close()


def test_from_stage_pelo_cliente_http_le_o_e3_do_run_base(
    client, tenant_minimal, artifact_db_session_factory, _plaintext_artifacts
):
    _seed_base_run_e3(client, artifact_db_session_factory, tenant_minimal)

    result = _categorize_tail_via_backend_client(client, tenant_minimal, pinned=True)

    assert result.success is True, result.error
    receitas = _tail_e4_receitas(artifact_db_session_factory)
    assert receitas is not None and receitas["total_transacoes"] > 0, receitas


def test_from_stage_sem_pin_aborta_no_guard_do_e4(
    client, tenant_minimal, artifact_db_session_factory, _plaintext_artifacts
):
    """Controle: sem o pin o E3 do base é invisível ao run de cauda (ADR-291 D5)."""
    _seed_base_run_e3(client, artifact_db_session_factory, tenant_minimal)

    result = _categorize_tail_via_backend_client(client, tenant_minimal, pinned=False)

    assert result.success is False
    assert "ADR-291" in (result.error or ""), result.error


def test_store_unavailable_returns_503(client, tmp_path, monkeypatch):
    from app.services import artifact_session

    def _db_down():
        raise RuntimeError("db down")

    monkeypatch.setattr(artifact_session, "_new_session", _db_down)

    r = client.post(
        "/api/v1/pipeline/stages/reconcile_transactions/execute",
        json={
            "run_id": "r1",
            "workspace_id": "ws1",
            "workspace_root": str(tmp_path),
        },
    )
    assert r.status_code == 503
    assert "ADR-303" in r.json()["detail"]
