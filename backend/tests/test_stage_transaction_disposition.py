"""ADR-357 §6 · ADR-256: o loop in-process decide o commit da transação pelo desfecho do stage."""

# Mesma tabela de `tests/test_cli_run_stage_disposition.py` (CLI do shell Go) e
# de `pipeline-service/tests/test_stage_transaction_disposition.py`: a paridade
# entre executores é ela valer nos três. Caminho de produção — o
# `InProcessPipelineClient` chama o `orchestrator._run_stage` real, que achata a
# exceção do runner em `success=False` — e só o runner é fake. Ele grava pela
# sessão do stage um artefato-sonda e uma row de `vehicles`, o padrão de
# `extract_comprovantes_bens`: a transação é do stage, não só dos artefatos.

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import func, select

import pipeline.orchestrator as orchestrator
from backend.app.models.pipeline_artifact import PipelineArtifact
from backend.app.models.pipeline_run import PipelineStageLog, PipelineStageStatus
from backend.app.models.vehicle import Vehicle
from backend.app.services.pipeline.pipeline_client import InProcessPipelineClient
from backend.tests.test_stage_degradation import seeded  # noqa: F401 — `seeded` é fixture

_PROBE_STAGE = "disposition_probe"
_REPO_CONFIG = Path(__file__).resolve().parents[2] / "config"


def _write_probe(ctx) -> None:
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


# Oráculo explícito: (stage executado, runner, a escrita sobrevive?, status do
# stage_log). O status prova que o caso tomou a rota pedida — um runner que
# falhasse por outro motivo (constraint, import) passaria como o cenário.
_CASES = (
    ("reconcile_transactions", _deliver, True, PipelineStageStatus.completed),
    ("reconcile_transactions", _raise_after_write, False, PipelineStageStatus.failed),
    ("reconcile_transactions", _report_failure, False, PipelineStageStatus.failed),
    ("extract_statements", _store_rejects_second_write, False, PipelineStageStatus.failed),
    ("validate_cross", _raise_after_write, True, PipelineStageStatus.degraded),
    ("generate_narratives", _raise_after_write, False, PipelineStageStatus.degraded),
)


@pytest.fixture
def _strict_repo_schemas(monkeypatch):
    """O schema do E2 só recusa em strict, e só com o config/ real do repo."""
    # Outro teste pode ter repontado `CONFIG_DIR` para um layout sem
    # `schema_validation` (`route_documents._init_config`), o que tornaria o
    # `write()` um no-op silencioso e o caso strict um caso de entrega.
    import scripts.pipeline_common as pc

    monkeypatch.setenv("MATHOMS_PIPELINE_SCHEMA_MODE", "strict")
    monkeypatch.setattr(pc, "CONFIG_DIR", _REPO_CONFIG)
    monkeypatch.setattr(pc, "_schema_registry", None)
    monkeypatch.delitem(pc._config_cache, "pipeline.json", raising=False)


def _drive_loop(seed, stage: str) -> None:
    """Um stage pelo loop real, executado pelo client in-process de produção."""
    from backend.app.tasks.pipeline_task import _execute_stages_loop

    client = InProcessPipelineClient()
    run_id, ws_id = seed["run_id"], seed["ws_id"]
    _execute_stages_loop(
        SimpleNamespace(artifact_store=None, root=seed["tmp_path"], pipeline_run_id=run_id),
        stages=[stage],
        run_id=run_id,
        ws_id=ws_id,
        skip_llm=False,
        stop_on_error=True,
        tier="premium",
        llm_stages=set(),
        run_stage_fn=lambda c, s: client.execute_stage(c, s, workspace_id=ws_id),
    )


async def _logged(seed, stage: str) -> tuple[PipelineStageStatus, str | None]:
    stmt = select(PipelineStageLog.status, PipelineStageLog.errors).where(
        PipelineStageLog.pipeline_run_id == seed["run_id"], PipelineStageLog.stage == stage
    )
    async with seed["async_session"]() as session:
        return tuple((await session.execute(stmt)).one())


async def _written(seed) -> tuple[int, int]:
    """(sondas do run, veículos do run) que sobreviveram ao fim do stage."""
    run_id = seed["run_id"]
    probes = select(func.count()).where(
        PipelineArtifact.pipeline_run_id == run_id, PipelineArtifact.stage == _PROBE_STAGE
    )
    vehicles = select(func.count()).where(Vehicle.modelo == run_id)
    async with seed["async_session"]() as session:
        return (await session.execute(probes)).scalar_one(), (
            await session.execute(vehicles)
        ).scalar_one()


@pytest.mark.asyncio
@pytest.mark.usefixtures("_strict_repo_schemas")
@pytest.mark.parametrize(
    ("stage", "runner", "survives", "status"),
    _CASES,
    ids=[f"{stage}-{runner.__name__.lstrip('_')}" for stage, runner, *_ in _CASES],
)
async def test_loop_in_process_decide_o_commit_pelo_desfecho(
    seeded,  # noqa: F811
    monkeypatch,
    stage,
    runner,
    survives,
    status,
):
    monkeypatch.setattr(orchestrator, "_get_stage_runner", lambda _stage: runner)

    _drive_loop(seeded, stage)

    logged_status, errors = await _logged(seeded, stage)
    assert logged_status == status
    if runner is _store_rejects_second_write:
        assert "strict" in errors, errors
    assert await _written(seeded) == (int(survives), int(survives))
