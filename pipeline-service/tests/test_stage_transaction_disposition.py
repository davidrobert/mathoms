"""ADR-357 §6 · ADR-256 · ADR-303 D1: o pipeline-service decide o commit pelo desfecho do stage."""

# Mesma tabela de `tests/test_cli_run_stage_disposition.py` (CLI do shell Go) e
# de `backend/tests/test_stage_transaction_disposition.py` (loop in-process): a
# paridade entre executores é ela valer nos três. As duas rotas abrem sessão
# própria por stage; o `orchestrator._run_stage` é o real, que achata a exceção
# do runner em `success=False`, e só o runner é fake. Os runners ficam aqui, não
# em `tests/fakes/` da raiz, porque o pacote `tests` deste serviço sombreia o de
# lá.

from __future__ import annotations

from pathlib import Path

import pytest

_PROBE_STAGE = "disposition_probe"
_WS_ID = "ws-disp"
_RUN_ID = "run-disp"
_REPO_CONFIG = Path(__file__).resolve().parents[2] / "config"


def _write_probe(ctx) -> None:
    from backend.app.models.vehicle import Vehicle

    store = ctx.artifact_store
    store.write(_PROBE_STAGE, ctx.pipeline_run_id, {"origem": "runner fake"})
    store.session.add(
        Vehicle(
            workspace_id=store.workspace_id,
            placa=ctx.pipeline_run_id[-7:],
            renavam="12345678900",
            marca="X",
            modelo=ctx.pipeline_run_id,
            ano_modelo=2024,
            ano_fabricacao=2024,
        )
    )


def _deliver(ctx) -> dict:
    _write_probe(ctx)
    return {"success": True}


def _report_failure(ctx) -> dict:
    _write_probe(ctx)
    return {"success": False}


def _raise_after_write(ctx) -> None:
    _write_probe(ctx)
    raise RuntimeError("fixture: o stage falha depois de escrever")


def _store_rejects_second_write(ctx) -> dict:
    _write_probe(ctx)
    ctx.artifact_store.write("extract_statements", ctx.pipeline_run_id, {})
    return {"success": True}


# Oráculo explícito: (stage executado, runner, a escrita sobrevive?).
_CASES = (
    ("reconcile_transactions", _deliver, True),
    ("reconcile_transactions", _raise_after_write, False),
    ("reconcile_transactions", _report_failure, False),
    ("extract_statements", _store_rejects_second_write, False),
    ("validate_cross", _raise_after_write, True),
    ("generate_narratives", _raise_after_write, False),
)

# Marca de onde veio cada não-entrega — sem ela, um caso que falhasse por outro
# motivo (runner ausente, constraint) passaria como se fosse o cenário pedido.
_ERROR_MARK = {
    _deliver: None,
    _raise_after_write: "fixture: o stage falha depois de escrever",
    _report_failure: None,
    _store_rejects_second_write: "strict",
}


@pytest.fixture
def _strict_repo_schemas(monkeypatch):
    """O schema do E2 só recusa em strict, e só com o config/ real do repo."""
    import scripts.pipeline_common as pc

    monkeypatch.setenv("MATHOMS_PIPELINE_SCHEMA_MODE", "strict")
    monkeypatch.setattr(pc, "CONFIG_DIR", _REPO_CONFIG)
    monkeypatch.setattr(pc, "_schema_registry", None)
    monkeypatch.delitem(pc._config_cache, "pipeline.json", raising=False)


@pytest.fixture
def _parents(artifact_db_session_factory):
    """Workspace + run reais: a sonda e o veículo apontam para eles (ADR-371)."""
    from backend.app.models.pipeline_run import PipelineRun, PipelineRunStatus
    from backend.app.models.user import User
    from backend.app.models.workspace import Workspace

    session = artifact_db_session_factory()
    try:
        owner = User(id="user-disp", email="disp@test.local", hashed_password="x", full_name="Disp")
        session.add(owner)
        session.flush()
        session.add(Workspace(id=_WS_ID, name="WS", owner_id=owner.id))
        session.add(PipelineRun(id=_RUN_ID, workspace_id=_WS_ID, status=PipelineRunStatus.running))
        session.commit()
    finally:
        session.close()


def _post_stage(client, workspace_root: Path, stage: str) -> dict:
    r = client.post(
        f"/api/v1/pipeline/stages/{stage}/execute",
        json={"run_id": _RUN_ID, "workspace_id": _WS_ID, "workspace_root": str(workspace_root)},
    )
    assert r.status_code == 200, r.text
    return r.json()


def _post_run(client, workspace_root: Path, stage: str) -> dict:
    r = client.post(
        "/api/v1/pipeline/runs",
        json={
            "run_id": _RUN_ID,
            "workspace_id": _WS_ID,
            "workspace_root": str(workspace_root),
            "stages": [stage],
            "skip_llm": False,
        },
    )
    assert r.status_code == 200, r.text
    (result,) = r.json()["stages"]
    return result


def _count_written(factory) -> tuple[int, int]:
    from backend.app.models.pipeline_artifact import PipelineArtifact
    from backend.app.models.vehicle import Vehicle

    session = factory()
    try:
        probes = (
            session.query(PipelineArtifact)
            .filter_by(pipeline_run_id=_RUN_ID, stage=_PROBE_STAGE)
            .count()
        )
        vehicles = session.query(Vehicle).filter_by(modelo=_RUN_ID).count()
        return probes, vehicles
    finally:
        session.close()


@pytest.mark.usefixtures("_strict_repo_schemas", "_parents")
@pytest.mark.parametrize("post", [_post_stage, _post_run], ids=["stage", "run"])
@pytest.mark.parametrize(
    ("stage", "runner", "survives"),
    _CASES,
    ids=[f"{stage}-{runner.__name__.lstrip('_')}" for stage, runner, _ in _CASES],
)
def test_pipeline_service_decide_o_commit_pelo_desfecho(
    client, tmp_path, artifact_db_session_factory, monkeypatch, post, stage, runner, survives
):
    import pipeline.orchestrator as orchestrator

    monkeypatch.setattr(orchestrator, "_get_stage_runner", lambda _stage: runner)

    result = post(client, tmp_path, stage)

    assert (result["stage"], result["success"]) == (stage, runner is _deliver)
    mark = _ERROR_MARK[runner]
    assert (result["error"] is None) if mark is None else (mark in result["error"]), result
    expected = (int(survives), int(survives))
    assert _count_written(artifact_db_session_factory) == expected
