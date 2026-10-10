"""ADR-291 · ADR-303 D2: o pin do from_stage sai dos args da task e chega aos dois executores."""

# O ctx é a fonte única do pin dentro do run: o loop abre o DBArtifactStore com ele
# e o HttpPipelineClient o reenvia no payload. Até 2026-10-09 só o store recebia o
# pin, e um from_stage sob o shell Go lia E3/E4/E5 do run corrente, que não os tem.
# Os dois casos passam pela task real: args → hidratação → ctx → consumidor.

from __future__ import annotations

import json

import httpx
import pytest

from backend.app.services.pipeline import pipeline_client as client_module
from backend.app.services.pipeline.pipeline_client import (
    FallbackPipelineClient,
    HttpPipelineClient,
    StageResult,
)
from backend.tests import factories

_STAGE = "categorize_transactions"
_E3_KEY = "banco_contacorrente_BRL_202601_202603"
_PIN = ["reconcile_transactions", "E3"]


def _write_e3(ws_id: str, run_id: str) -> None:
    from backend.app.core.database import SyncSessionLocal
    from backend.app.services.storage.db_artifact_store import DBArtifactStore

    with SyncSessionLocal() as session:
        store = DBArtifactStore(session, workspace_id=ws_id, pipeline_run_id=run_id)
        store.write("reconcile_transactions", _E3_KEY, {"banco": "banco", "transacoes": []})
        session.commit()


async def _seed(db) -> dict:
    """Run base com um E3 commitado + o run de cauda (pending) que o lê pelo pin."""
    ws = await factories.make_workspace(db)
    base = await factories.make_run(db, workspace=ws, status="completed")
    tail = await factories.make_run(db, workspace=ws, status="pending")
    await db.commit()
    _write_e3(ws.id, base.id)
    return {"ws_id": ws.id, "base_run_id": base.id, "run_id": tail.id}


def _run_task(seed: dict, tmp_path, monkeypatch, client) -> None:
    import backend.app.tasks.pipeline_task as task_module

    monkeypatch.setattr(client_module, "_SINGLETON", client)
    monkeypatch.setattr(task_module, "_finalize_pipeline_outcome", lambda *a, **k: None)
    task_module.run_pipeline_task.run(
        run_id=seed["run_id"],
        ws_id=seed["ws_id"],
        tenant_root_str=str(tmp_path),
        config_dir_str=str(tmp_path / "config"),
        stages=[_STAGE],
        skip_llm=True,
        stop_on_error=True,
        tier="premium",
        base_run_id=seed["base_run_id"],
        base_run_fallback_stages=_PIN,
    )


@pytest.mark.asyncio
async def test_payload_do_shell_carrega_o_pin_dos_args_da_task(db, tmp_path, monkeypatch):
    seed = await _seed(db)
    bodies: list[dict] = []

    def _shell(req: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(req.content.decode()))
        return httpx.Response(200, json={"stage": _STAGE, "success": True})

    http = httpx.Client(transport=httpx.MockTransport(_shell))
    _run_task(seed, tmp_path, monkeypatch, HttpPipelineClient("http://ps.local", http=http))

    assert [b["base_run_id"] for b in bodies] == [seed["base_run_id"]]
    assert bodies[0]["base_run_fallback_stages"] == sorted(_PIN)


class _InProcessReadsE3:
    """Stand-in do InProcess: lê o E3 pelo store que o loop injetou no ctx."""

    def __init__(self) -> None:
        self.e3: list = []

    def execute_stage(self, ctx, stage: str, *, workspace_id: str) -> StageResult:
        self.e3.append(ctx.artifact_store.read("reconcile_transactions", _E3_KEY))
        return StageResult(stage=stage, success=True)

    def is_llm_stage(self, stage: str) -> bool:
        return False


@pytest.mark.asyncio
async def test_degrade_para_inprocess_le_o_e3_do_run_base(db, tmp_path, monkeypatch):
    """ADR-323: com o shell fora, o InProcess usa o store do loop — pinado pelo mesmo ctx."""
    seed = await _seed(db)

    def _shell_down(req: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("shell down")

    inprocess = _InProcessReadsE3()
    http = httpx.Client(transport=httpx.MockTransport(_shell_down))
    client = FallbackPipelineClient(HttpPipelineClient("http://ps.local", http=http), inprocess)
    _run_task(seed, tmp_path, monkeypatch, client)

    assert len(inprocess.e3) == 1
    assert inprocess.e3[0] is not None, "o store do loop perdeu o pin do run base"
    assert inprocess.e3[0]["banco"] == "banco"
