"""ADR-443 — o stage roda uma vez por run, nos dois executores: não há retry de stage."""

# Os fakes que levantavam direto no `run_stage_fn` pulavam o `except Exception` de
# `orchestrator._run_stage`, e foi assim que `STAGE_RETRY_CONFIGS` ficou inerte
# in-process com a suíte verde. Aqui a composição é a de `run_pipeline_task`:
# `_execute_stages_loop` → `get_pipeline_client()` → `_run_stage` → runner. Só a
# folha é trocada (in-process) ou só o transporte (HTTP, via `MockTransport`).

from __future__ import annotations

import uuid
from collections import Counter
from types import SimpleNamespace
from unittest.mock import patch

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import select

from backend.app.core.security import hash_password
from backend.app.models.pipeline_run import PipelineRun, PipelineRunStatus, PipelineStageLog
from backend.app.models.user import User
from backend.app.models.workspace import Workspace
from backend.app.services.pipeline import pipeline_client as pc
from backend.tests.test_pipeline_task import _build_file_backed_engines
from pipeline.llm.error_classification import LLMError, LLMErrorType
from pipeline.stage_outcome import DEGRADABLE, stage_criticality
from pipeline.stage_spec import FULL_ORDER, STAGE_REGISTRY

_LLM_STAGES = [name for name in FULL_ORDER if STAGE_REGISTRY[name].is_llm]

# Forma que `LLMService.call` levanta ao esgotar as próprias tentativas
# (`pipeline/llm/litellm_client.py`), com o transiente mais comum em pico — o
# overload, que a tabela apagada casava pelo needle `overloaded`.
_OVERLOAD = (
    "LLM call failed after 4 attempts (48231ms): litellm.InternalServerError: "
    "AnthropicException - {'type': 'error', 'error': {'type': 'overloaded_error'}}"
)


def _owner() -> User:
    return User(
        id=str(uuid.uuid4()),
        email=f"run_once_{uuid.uuid4().hex[:6]}@test.com",
        hashed_password=hash_password("pass"),
        full_name="RunOnce",
    )


async def _seed_running_run(async_session_factory) -> dict:
    async with async_session_factory() as session:
        user = _owner()
        ws = Workspace(id=str(uuid.uuid4()), owner_id=user.id, name="WS")
        run = PipelineRun(
            id=str(uuid.uuid4()), workspace_id=ws.id, status=PipelineRunStatus.running
        )
        for row in (user, ws, run):
            session.add(row)
            await session.flush()
        await session.commit()
        return {"ws_id": ws.id, "run_id": run.id}


@pytest_asyncio.fixture
async def seeded_run(tmp_path):
    import backend.app.tasks.pipeline_task as task_module

    engines = await _build_file_backed_engines(tmp_path / "run_once.db")
    async_engine, sync_engine, async_session, sync_session = engines
    seed = await _seed_running_run(async_session)
    seed["sync_session"] = sync_session
    with patch.object(task_module, "SyncSessionLocal", sync_session):
        yield seed
    await async_engine.dispose()
    sync_engine.dispose()


@pytest.fixture
def no_backoff(monkeypatch):
    import backend.app.tasks.pipeline_task as pt

    monkeypatch.setattr(pt.time, "sleep", lambda s: pytest.fail(f"backoff de stage dormiu {s}s"))


@pytest.fixture
def production_run_stage_fn(monkeypatch, seeded_run):
    """O `_exec_stage` de `run_pipeline_task`, com o client que o deploy atual resolve."""
    monkeypatch.delenv("MATHOMS_PIPELINE_SERVICE_URL", raising=False)
    pc.reset_pipeline_client()
    client = pc.get_pipeline_client()
    assert isinstance(client, pc.InProcessPipelineClient)
    yield lambda c, s: client.execute_stage(c, s, workspace_id=seeded_run["ws_id"])
    pc.reset_pipeline_client()


def _install_raising_leaf(monkeypatch) -> Counter:
    """Troca só o runner — o `_run_stage` real continua no meio da composição."""
    import pipeline.orchestrator as orchestrator

    calls: Counter = Counter()

    def _leaf_for(stage: str):
        def _runner(_ctx):
            calls[stage] += 1
            raise LLMError(_OVERLOAD, LLMErrorType.provider_error, retryable=False)

        return _runner

    monkeypatch.setattr(orchestrator, "_get_stage_runner", _leaf_for)
    return calls


def _run_llm_stages(seed: dict, run_stage_fn, root) -> tuple[bool, bool]:
    from backend.app.tasks.pipeline_task import _execute_stages_loop

    ctx = SimpleNamespace(artifact_store=None, root=root, pipeline_run_id=seed["run_id"])
    return _execute_stages_loop(
        ctx,
        stages=_LLM_STAGES,
        run_id=seed["run_id"],
        ws_id=seed["ws_id"],
        skip_llm=False,
        stop_on_error=False,
        tier="premium",
        llm_stages=set(_LLM_STAGES),
        run_stage_fn=run_stage_fn,
    )


def _status_by_stage(seed: dict) -> dict[str, str]:
    query = select(PipelineStageLog).where(PipelineStageLog.pipeline_run_id == seed["run_id"])
    with seed["sync_session"]() as db:
        return {log.stage: log.status.value for log in db.execute(query).scalars()}


@pytest.mark.asyncio
async def test_stage_llm_que_levanta_transiente_roda_uma_vez(
    seeded_run, production_run_stage_fn, no_backoff, monkeypatch, tmp_path
):
    calls = _install_raising_leaf(monkeypatch)

    has_failure, paused = _run_llm_stages(seeded_run, production_run_stage_fn, tmp_path)

    assert calls == Counter({stage: 1 for stage in _LLM_STAGES})
    assert has_failure and not paused
    assert _status_by_stage(seeded_run) == {
        s: "degraded" if stage_criticality(s) == DEGRADABLE else "failed" for s in _LLM_STAGES
    }


def _raising(exc_type, message: str):
    def _handler(request: httpx.Request) -> httpx.Response:
        raise exc_type(message, request=request)

    return _handler


def _responding(status: int):
    def _handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json={"detail": "executor_unavailable"})

    return _handler


# Em `main` até a ADR-443, cada caso fazia 3 POSTs com backoff 10/20s: a tabela
# casava o texto da falha de TRANSPORTE com needles de LLM. Os dois primeiros são
# a classe que a ADR-323 §2 recusa re-executar (o stage pode seguir rodando no
# shell e commitar depois) e passavam com o fallback ligado; com ele desligado, a
# falha do shell é o sinal do soak que a §6 protege.
_SHELL_FAILURES = [
    pytest.param(
        _raising(httpx.RemoteProtocolError, "Server disconnected without sending a response."),
        True,
        id="server-disconnected-fallback-on",
    ),
    pytest.param(_raising(httpx.ReadTimeout, "timed out"), True, id="read-timeout-fallback-on"),
    pytest.param(
        _raising(httpx.ConnectError, "[Errno 61] Connection refused"),
        False,
        id="connect-error-fallback-off",
    ),
    pytest.param(_responding(503), False, id="http-503-fallback-off"),
]


def _http_client(handler, *, fallback: bool) -> pc.PipelineServiceClient:
    transport = httpx.MockTransport(handler)
    http = pc.HttpPipelineClient("http://shell", http=httpx.Client(transport=transport))
    return pc.FallbackPipelineClient(http, pc.InProcessPipelineClient()) if fallback else http


@pytest.mark.parametrize(("shell_failure", "fallback"), _SHELL_FAILURES)
def test_falha_do_shell_nao_reexecuta_o_stage(shell_failure, fallback, no_backoff, tmp_path):
    from backend.app.tasks.pipeline_task import _run_stage_once

    posts: list[str] = []

    def _counting(request: httpx.Request) -> httpx.Response:
        posts.append(request.url.path)
        return shell_failure(request)

    client = _http_client(_counting, fallback=fallback)
    ctx = SimpleNamespace(
        pipeline_run_id="run", root=tmp_path, config_dir=None, shell_degraded=False
    )
    result, error_msg, _tb, _reason = _run_stage_once(
        ctx, "extract_with_llm", lambda c, s: client.execute_stage(c, s, workspace_id="ws")
    )

    assert result is None and error_msg
    assert len(posts) == 1


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="ADR-443 §Deferimento: o executor achata a exceção do runner e a classe se perde",
)
def test_classe_da_falha_do_runner_sobrevive_ao_executor(monkeypatch, tmp_path):
    """Vermelho por desenho até o §Deferimento fechar — ao virar XPASS, reescreva o §8.1 do runbook do flip strict."""
    from backend.app.services.pipeline.stage_failure_reason import reason_from_stage_detail

    _install_raising_leaf(monkeypatch)
    ctx = SimpleNamespace(root=tmp_path, pipeline_run_id="run")

    result = pc.InProcessPipelineClient().execute_stage(ctx, "extract_with_llm", workspace_id="ws")

    assert reason_from_stage_detail(result.detail).value == "provider_error"
