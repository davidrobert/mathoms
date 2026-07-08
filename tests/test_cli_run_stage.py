"""A3.cli (ADR-150 §4): CLI ``run-stage`` do orchestrator via subprocess real.

Gates do track ``a3cli-orchestrator-cli`` Fase 1: execução de stage real com
artefato persistido em ``pipeline_artifacts``, paridade de shape com o
``StageResult`` programático, fail-fast estruturado (ADR-303 D4), fallback de
leitura no run base (ADR-291/ADR-303 D2) e validação de stage.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
_E2_FIXTURE = (
    REPO_ROOT / "tests" / "fixtures" / "pipeline_golden" / "e2" / "minimal-extrato-2_extract.json"
)
_WORKSPACE_ID = "ws-cli"


@pytest.fixture
def tenant_minimal(tmp_path: Path) -> Path:
    """Workspace com config mínima (espelho do teste de integração ADR-303)."""
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
def artifact_db(tmp_path: Path) -> str:
    """SQLite em arquivo com schema criado, na URL async que MATHOMS_DATABASE_URL exige."""
    # O backend constrói engine async no import; o sync deriva via
    # settings.sync_database_url (strip de +aiosqlite).
    from sqlalchemy import create_engine

    import backend.app.models  # noqa: F401 — registra tabelas no metadata
    from backend.app.core.database import Base

    db_path = tmp_path / "artifacts.db"
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)
    engine.dispose()
    return f"sqlite+aiosqlite:///{db_path}"


def _open_store(db_url: str, run_id: str):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from backend.app.services.storage.db_artifact_store import DBArtifactStore

    engine = create_engine(db_url.replace("+aiosqlite", ""))
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    return session, DBArtifactStore(session, workspace_id=_WORKSPACE_ID, pipeline_run_id=run_id)


def _seed_e2(db_url: str, run_id: str, monkeypatch, valor: float = 100.0) -> None:
    from backend.app.core.config import settings

    monkeypatch.setattr(settings, "ENCRYPT_PIPELINE_ARTIFACTS", False)
    payload = json.loads(_E2_FIXTURE.read_text(encoding="utf-8"))
    payload["transacoes"][0]["valor"] = valor
    payload["saldo_inicial"] = 0.0
    payload["saldo_final"] = valor
    session, store = _open_store(db_url, run_id)
    try:
        store.write("E2-extratos", "golden-minimal", payload)
        session.commit()
    finally:
        session.close()


_TEST_FERNET_KEY = "NwHpLJlLGSeC7NIS6gfVdVSYh_pObKqY4G_CwkQ1kuA="


def _cli_env(db_url: str | None) -> dict[str, str]:
    env = {
        **os.environ,
        "MATHOMS_ENCRYPT_PIPELINE_ARTIFACTS": "false",
        # Hidratação (run_context_factory) exige o vault Fernet (config_materializer).
        "MATHOMS_FERNET_KEY": _TEST_FERNET_KEY,
        # Porta fechada: caches Redis (catálogo, budget) viram no-op fail-open —
        # sem isso a hidratação do subprocess escreveria no Redis dev (ex.:
        # catálogo vazio por cima do real em institution_catalog:global).
        "MATHOMS_REDIS_URL": "redis://127.0.0.1:6390/0",
        "PYTHONPATH": str(REPO_ROOT),
    }
    env.pop("MATHOMS_DATABASE_URL", None)
    if db_url is not None:
        env["MATHOMS_DATABASE_URL"] = db_url
    return env


def _run_cli(args: list[str], db_url: str | None) -> subprocess.CompletedProcess:
    cmd = [sys.executable, "-m", "pipeline.orchestrator", *args]
    return subprocess.run(
        cmd, capture_output=True, text=True, cwd=REPO_ROOT, env=_cli_env(db_url), timeout=180
    )


def _run_stage_args(workspace: Path, run_id: str) -> list[str]:
    return [
        "run-stage",
        "reconcile_transactions",
        "--workspace",
        str(workspace),
        "--run-id",
        run_id,
        "--workspace-id",
        _WORKSPACE_ID,
    ]


def _list_e3_keys(db_url: str, run_id: str) -> list[str]:
    session, store = _open_store(db_url, run_id)
    try:
        return store.list_keys("E3")
    finally:
        session.close()


def _read_single_e3(db_url: str, run_id: str) -> dict:
    session, store = _open_store(db_url, run_id)
    try:
        keys = store.list_keys("E3")
        assert len(keys) == 1, f"expected one E3 key for {run_id}, got {keys}"
        return store.read("E3", keys[0])
    finally:
        session.close()


def test_cli_executes_stage_and_persists_artifact(tenant_minimal, artifact_db, monkeypatch):
    _seed_e2(artifact_db, "run-cli", monkeypatch)

    proc = _run_cli(_run_stage_args(tenant_minimal, "run-cli"), artifact_db)

    assert proc.returncode == 0, proc.stderr
    stdout_lines = [l for l in proc.stdout.splitlines() if l]
    assert len(stdout_lines) == 1, f"stdout deve conter só o JSON do StageResult: {proc.stdout!r}"
    result = json.loads(stdout_lines[0])
    assert (result["stage"], result["success"]) == ("reconcile_transactions", True)

    persisted = _read_single_e3(artifact_db, "run-cli")
    assert persisted["banco"] == "itau"
    assert persisted["transacoes"][0]["valor"] == 100.0


def test_cli_stdout_has_stage_result_shape_parity(tenant_minimal, artifact_db, monkeypatch):
    """CLI é interface versionada: stdout == shape exato do StageResult programático."""
    from pipeline.orchestrator import StageResult

    canonical = set(asdict(StageResult(stage="x", success=True)))
    assert canonical == {"stage", "success", "duration_ms", "detail", "error"}, (
        "StageResult mudou de shape — bump consciente exigido: atualize o CLI "
        "(pipeline/cli_run_stage.py), o contrato do pipeline-service e este snapshot juntos."
    )

    _seed_e2(artifact_db, "run-shape", monkeypatch)
    proc = _run_cli(_run_stage_args(tenant_minimal, "run-shape"), artifact_db)
    assert proc.returncode == 0, proc.stderr
    assert set(json.loads(proc.stdout)) == canonical


def test_cli_fails_fast_without_database_url(tenant_minimal):
    proc = _run_cli(_run_stage_args(tenant_minimal, "run-x"), db_url=None)

    assert proc.returncode == 2
    assert proc.stdout == ""
    err = json.loads(proc.stderr)
    assert err["error"] == "environment"
    assert "MATHOMS_DATABASE_URL" in err["message"]
    assert err["adr"] == "ADR-303 D4"


def _seed_two_e2_versions(db_url: str, monkeypatch) -> None:
    _seed_e2(db_url, "run-base", monkeypatch, valor=100.0)
    _seed_e2(db_url, "run-mais-recente", monkeypatch, valor=999.0)


def test_cli_without_pin_reads_latest_workspace_artifact(tenant_minimal, artifact_db, monkeypatch):
    """Sem --base-run-id, o fallback workspace-scoped (ADR-241) lê a versão mais recente."""
    _seed_two_e2_versions(artifact_db, monkeypatch)

    proc = _run_cli(_run_stage_args(tenant_minimal, "run-sem-pin"), artifact_db)

    assert proc.returncode == 0, proc.stderr
    assert _read_single_e3(artifact_db, "run-sem-pin")["transacoes"][0]["valor"] == 999.0


def test_cli_base_run_id_pins_input_to_base_run(tenant_minimal, artifact_db, monkeypatch):
    """--base-run-id pina a leitura de E2 no run base (ADR-291), vencendo o workspace-latest."""
    _seed_two_e2_versions(artifact_db, monkeypatch)

    proc = _run_cli(
        [
            *_run_stage_args(tenant_minimal, "run-pinado"),
            "--base-run-id",
            "run-base",
            "--base-run-fallback-stages",
            "E2-extratos,E2-faturas",
        ],
        artifact_db,
    )

    assert proc.returncode == 0, proc.stderr
    assert json.loads(proc.stdout)["success"] is True
    assert _read_single_e3(artifact_db, "run-pinado")["transacoes"][0]["valor"] == 100.0


def test_cli_unknown_stage_exits_2_listing_valid(tenant_minimal, artifact_db):
    proc = _run_cli(
        [
            "run-stage",
            "stage_inexistente",
            "--workspace",
            str(tenant_minimal),
            "--run-id",
            "r",
            "--workspace-id",
            _WORKSPACE_ID,
        ],
        artifact_db,
    )
    assert proc.returncode == 2
    err = json.loads(proc.stderr)
    assert err["error"] == "unknown_stage"
    assert "reconcile_transactions" in err["message"]


def test_cli_help_works_without_backend_env():
    proc = _run_cli(["run-stage", "--help"], db_url=None)
    assert proc.returncode == 0
    assert "--workspace" in proc.stdout
