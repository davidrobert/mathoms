"""A40.l96 ([[ADR-430]] §5) — o hint do E1 alcança o E4 do MESMO run, não do seguinte."""

# `config_overrides` congela UMA vez por run, em `run_context_factory`, antes de
# qualquer stage. Sem a reinjeção pós-E1 o hint só chegaria ao run SEGUINTE — e o
# critério "run novo do workspace de dogfood publica abaixo do piso" passaria por
# ACIDENTE, porque lá o E1 já rodou antes. Este teste é o que o critério pede:
# workspace NOVO, E1 na mesma execução, loop de stages real.

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import patch

import pytest
import pytest_asyncio

from backend.app.models.family_member import FamilyMember
from backend.app.models.pipeline_run import PipelineRun, PipelineRunStatus
from backend.app.models.workspace import Workspace
from backend.tests.test_stage_redelivery_idempotency import (
    _build_file_backed_engines,
    _make_user_row,
)
from pipeline.orchestrator import StageResult

_CONTA_E1 = {
    "member_key": "rafael",
    "institution_code": "itau",
    "account_type": "extratoconta",
    "account_number_raw": "12345-6",
    "agency": None,
    "is_joint": False,
    "co_titulares": [],
}


def _rows_do_workspace_novo() -> tuple[list, str, str]:
    """Workspace SEM curadoria — `bank_accounts` vazio, que é o default real."""
    user = _make_user_row()
    ws = Workspace(id=str(uuid.uuid4()), owner_id=user.id, name="WS")
    run = PipelineRun(
        id=str(uuid.uuid4()),
        workspace_id=ws.id,
        status=PipelineRunStatus.running,
        total_documents=1,
    )
    membro = FamilyMember(
        workspace_id=ws.id,
        key="rafael_pereira_souza",
        full_name="Rafael Pereira Souza",
        short_name="Rafael",
        role="titular",
        order=0,
    )
    return [user, ws, run, membro], ws.id, run.id


async def _seed_workspace_novo(async_session_factory) -> dict:
    rows, ws_id, run_id = _rows_do_workspace_novo()
    async with async_session_factory() as session:
        session.add_all(rows)
        await session.commit()
        return {"ws_id": ws_id, "run_id": run_id}


@pytest_asyncio.fixture
async def run_novo(tmp_path):
    import backend.app.tasks.pipeline_task as task_module

    engines = await _build_file_backed_engines(tmp_path / "lag.db")
    async_engine, sync_engine, async_session, sync_session = engines
    seed = await _seed_workspace_novo(async_session)
    with patch.object(task_module, "SyncSessionLocal", sync_session):
        yield seed
    await async_engine.dispose()
    sync_engine.dispose()


def _stage_e1_escreve_members(ctx, stage):
    """Faz o que o E1 real faz: grava `members` com `contas[]` no artifact store."""
    ctx.artifact_store.write(
        stage,
        "members",
        {
            "membros": {"rafael": {"nome_completo": "Rafael Pereira Souza", "papel": "titular"}},
            "contas": [_CONTA_E1],
            "titular": "rafael",
        },
    )
    return StageResult(stage=stage, success=True, duration_ms=1.0, detail={"ok": True})


def _roda_e1(ctx, seed) -> bool:
    """Roda o loop REAL com um único stage E1. Devolve `has_failure`."""
    from backend.app.tasks.pipeline_task import _execute_stages_loop

    has_failure, _ = _execute_stages_loop(
        ctx,
        stages=["extract_members"],
        run_id=seed["run_id"],
        ws_id=seed["ws_id"],
        skip_llm=False,
        stop_on_error=True,
        tier="premium",
        llm_stages=set(),
        run_stage_fn=_stage_e1_escreve_members,
    )
    return has_failure


@pytest.mark.asyncio
async def test_hint_do_e1_alcanca_o_config_do_mesmo_run(run_novo):
    ctx = SimpleNamespace(artifact_store=None, config_overrides={"family_members.json": {}})
    assert not _roda_e1(ctx, run_novo), "o stage E1 falhou — o teste mediria outra coisa"

    blob = ctx.config_overrides["family_members.json"]
    contas = blob.get("contas") or []
    assert contas, "o E4 deste MESMO run enxergaria o mapa vazio — o lag não foi fechado"
    assert contas[0]["institution_code"] == "itau"
    assert contas[0]["origem"] == "irpf_hint"
    # D3: a chave curta do artefato E1 chega ao E4 já canonicalizada.
    assert contas[0]["member_key"] == "rafael_pereira_souza"
