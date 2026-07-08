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
