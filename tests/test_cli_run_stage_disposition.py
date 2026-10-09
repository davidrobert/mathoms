"""ADR-357 §6 · ADR-256 · ADR-303 D1: o CLI do shell Go decide o commit pelo desfecho do stage."""

# `orchestrator._run_stage` achata a exceção do runner em `success=False`, então o
# `except BaseException` do `_run_with_store` nunca via a falha, e o commit levava
# o que o stage escreveu antes de não entregar. A row nova vira o "latest" do
# fallback da ADR-241, aposenta a versão boa anterior (`retention_until`) e
# habilita o run como base de `from_stage` (`_resolve_base_run`, ADR-291). Um
# filho Python real roda os casos: `main()` do CLI, sessão do backend e SQLite em
# arquivo são os de produção; só o runner é fake.
#
# A mesma tabela vale no loop in-process
# (`backend/tests/test_stage_transaction_disposition.py`) e no pipeline-service
# (`pipeline-service/tests/test_stage_transaction_disposition.py`): a paridade
# entre executores é ela valer nos três.

from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from pathlib import Path

from tests.fakes.stage_disposition import PROBE_STAGE
from tests.test_cli_run_stage import (  # noqa: F401 — `artifact_db`/`tenant_minimal` são fixtures
    _WORKSPACE_ID,
    REPO_ROOT,
    _cli_env,
    _ensure_parents,
    _open_store,
    artifact_db,
    tenant_minimal,
)

_PRIOR_RUN = "run-anterior"

# Oráculo explícito: (run_id, stage executado, runner, a escrita sobrevive?). Não
# deriva do registry nem do predicado — se a declaração de um stage mudar, esta
# tabela muda junto, porque é a decisão que ela trava.
_CASES = (
    ("disp-1", "reconcile_transactions", "deliver", True),
    ("disp-2", "reconcile_transactions", "raise_after_write", False),
    ("disp-3", "reconcile_transactions", "report_failure", False),
    ("disp-4", "extract_statements", "store_rejects_second_write", False),
    ("disp-5", "validate_cross", "raise_after_write", True),
    ("disp-6", "generate_narratives", "raise_after_write", False),
)

# Marca de onde veio cada não-entrega — sem ela, um caso que falhasse por outro
# motivo (runner ausente, constraint) passaria como se fosse o cenário pedido.
_ERROR_MARK = {
    "deliver": None,
    "raise_after_write": "fixture: o stage falha depois de escrever",
    "report_failure": None,
    "store_rejects_second_write": "strict",
}

_CHILD = (
    "import json, sys\n"
    "from tests.fakes.stage_disposition import run_cli_cases\n"
    "print(json.dumps(run_cli_cases(sys.argv[1])))\n"
)


def _argv(tenant: Path, run_id: str, stage: str) -> list[str]:
    return [
        "run-stage",
        stage,
        "--workspace",
        str(tenant),
        "--run-id",
        run_id,
        "--workspace-id",
        _WORKSPACE_ID,
    ]


def _seed_prior_versions(db_url: str, monkeypatch) -> None:
    """Versão boa de cada chave-sonda num run anterior — a que um parcial aposentaria."""
    from backend.app.core.config import settings

    monkeypatch.setattr(settings, "ENCRYPT_PIPELINE_ARTIFACTS", False)
    session, store = _open_store(db_url, _PRIOR_RUN)
    try:
        for run_id, *_ in _CASES:
            store.write(PROBE_STAGE, run_id, {"origem": "run anterior"})
        session.commit()
    finally:
        session.close()


def _run_child(tenant: Path, db_url: str) -> list[dict]:
    for run_id, *_ in _CASES:
        _ensure_parents(db_url, run_id)
    cases = [[stage, runner, _argv(tenant, run_id, stage)] for run_id, stage, runner, _ in _CASES]
    # O schema do E2 só recusa em strict; o config/ do repo só vale sem workspace root.
    env = {**_cli_env(db_url), "MATHOMS_PIPELINE_SCHEMA_MODE": "strict"}
    env.pop("MATHOMS_WORKSPACE_ROOT", None)
    proc = subprocess.run(
        [sys.executable, "-c", _CHILD, json.dumps(cases)],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        env=env,
        timeout=180,
    )
    assert proc.returncode == 0, proc.stderr[-3000:]
    return json.loads(proc.stdout.splitlines()[-1])


def _stage_result(outcome: dict) -> dict:
    lines = [line for line in outcome["stdout"].splitlines() if line]
    assert len(lines) == 1, f"stdout deve ter só o StageResult: {outcome!r}"
    return json.loads(lines[0])


def _assert_ran_the_intended_scenario(outcomes: list[dict]) -> None:
    for (run_id, stage, runner, _), outcome in zip(_CASES, outcomes, strict=True):
        result = _stage_result(outcome)
        delivered = runner == "deliver"
        assert (outcome["exit_code"], result["stage"], result["success"]) == (
            0 if delivered else 1,
            stage,
            delivered,
        ), f"{run_id}: {result!r}"
        mark = _ERROR_MARK[runner]
        assert (
            (result["error"] is None) if mark is None else (mark in result["error"])
        ), f"{run_id}: {result['error']!r}"


def _observe(conn: sqlite3.Connection, run_id: str) -> tuple[int, int, bool]:
    """(sondas do run, veículos do run, versão anterior aposentada?)."""
    (probes,) = conn.execute(
        "SELECT COUNT(*) FROM pipeline_artifacts WHERE pipeline_run_id = ? AND stage = ?",
        (run_id, PROBE_STAGE),
    ).fetchone()
    (vehicles,) = conn.execute(
        "SELECT COUNT(*) FROM vehicles WHERE modelo = ?", (run_id,)
    ).fetchone()
    (retired,) = conn.execute(
        "SELECT retention_until IS NOT NULL FROM pipeline_artifacts "
        "WHERE pipeline_run_id = ? AND stage = ? AND artifact_key = ?",
        (_PRIOR_RUN, PROBE_STAGE, run_id),
    ).fetchone()
    return probes, vehicles, bool(retired)


def test_cli_decide_o_commit_pelo_desfecho_do_stage(tenant_minimal, artifact_db, monkeypatch):  # noqa: F811
    _seed_prior_versions(artifact_db, monkeypatch)

    outcomes = _run_child(tenant_minimal, artifact_db)

    _assert_ran_the_intended_scenario(outcomes)
    conn = sqlite3.connect(artifact_db.split(":///", 1)[1])
    try:
        observed = {run_id: _observe(conn, run_id) for run_id, *_ in _CASES}
    finally:
        conn.close()
    expected = {
        run_id: (int(survives), int(survives), survives) for run_id, _, _, survives in _CASES
    }
    assert observed == expected
