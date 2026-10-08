"""Erro de banco num stage não chega com valor ao stage_log, ao canal do WS nem ao traceback.

`str(StatementError)` carrega `[parameters: ...]` e, no Postgres, o DETAIL do driver
(`Key (...)=(...)`, `Failing row contains (...)`). Medido em 2026-10-08 em PG 16:
`match_or_create` com `codigo_rfb='01-12'` levantou `DataError` com endereço e nome
no texto — e o texto ia cru para `pipeline_stage_logs` (plaintext, enquanto o
artefato é Fernet — ADR-231) e para o pub/sub.

Os testes dirigem o loop REAL. No caminho de produção, o orchestrator REAL: o
`except` de `pipeline.orchestrator._run_stage` engole a exceção e devolve
`StageResult.error` — ela nunca chega a `_run_stage_with_retry`. Um teste com
`run_stage_fn` que levanta direto provaria só o caminho que produção não percorre.
"""

from __future__ import annotations

import json
import uuid
from types import SimpleNamespace
from unittest.mock import patch

import pytest_asyncio
from psycopg.errors import OperationalError as PgOperationalError
from psycopg.errors import UniqueViolation
from sqlalchemy import Column, MetaData, String, Table, create_engine, insert, select
from sqlalchemy.exc import IntegrityError, OperationalError

from backend.app.core.security import hash_password
from backend.app.models.pipeline_run import (
    PipelineRun,
    PipelineRunStatus,
    PipelineStageLog,
    PipelineStageStatus,
)
from backend.app.models.user import User
from backend.app.models.workspace import Workspace
from backend.tests.test_pipeline_task import _build_file_backed_engines

# Sintéticos, PII-zero: o que importa é que são bound parameter / chave do DETAIL.
_ENDERECO = "Rua Exemplo, 100"
_TITULAR = "maria exemplo"
_VALORES = (_ENDERECO, _TITULAR)
_STAGE = "consolidate_baseline"


class _CanalGravado:
    """Redis fake: guarda o JSON exato que iria para o canal ``pipeline:{run_id}``."""

    def __init__(self) -> None:
        self.mensagens: list[str] = []

    def publish(self, _canal: str, mensagem: str) -> None:
        self.mensagens.append(mensagem)


def _quebra_no_banco(_ctx) -> None:
    """INSERT duplicado num engine SEM ``hide_parameters``: o valor vai no texto do erro."""
    eng = create_engine("sqlite://")
    tabela = Table(
        "identidade_imovel",
        MetaData(),
        Column("titular_key", String, primary_key=True),
        Column("descricao_sample", String),
    )
    tabela.metadata.create_all(eng)
    linha = {"titular_key": _TITULAR, "descricao_sample": _ENDERECO}
    try:
        for _ in range(2):
            with eng.begin() as conn:
                conn.execute(insert(tabela), linha)
    finally:
        eng.dispose()


def _unique_violation_com_detail() -> IntegrityError:
    """O DETAIL do Postgres carrega a chave — ``hide_parameters`` não o alcança."""
    orig = UniqueViolation(
        'duplicate key value violates unique constraint "uq_property_identity_key"\n'
        f"DETAIL:  Key (titular_key, endereco_canonical)=({_TITULAR}, {_ENDERECO}) "
        "already exists."
    )
    exc = IntegrityError("INSERT INTO property_identities ...", None, orig, hide_parameters=True)
    exc.__cause__ = orig
    return exc


def _queda_de_conexao() -> OperationalError:
    """Transiente casável pelo retry (`connection`), com o endereço no bound parameter."""
    orig = PgOperationalError("connection to server at db:5432 was lost")
    return OperationalError("UPDATE property_identities ...", {"descricao": _ENDERECO}, orig)


async def _seed(async_session_factory) -> dict:
    async with async_session_factory() as session:
        user = User(
            id=str(uuid.uuid4()),
            email=f"stage_pii_{uuid.uuid4().hex[:6]}@test.com",
            hashed_password=hash_password("pass"),
            full_name="StagePii",
        )
        ws = Workspace(id=str(uuid.uuid4()), owner_id=user.id, name="WS")
        run = PipelineRun(
            id=str(uuid.uuid4()),
            workspace_id=ws.id,
            status=PipelineRunStatus.running,
        )
        session.add_all([user, ws, run])
        await session.commit()
        return {"ws_id": ws.id, "run_id": run.id}


@pytest_asyncio.fixture
async def seeded(tmp_path):
    import backend.app.services.pipeline.events as events_module
    import backend.app.tasks.pipeline_task as task_module

    async_engine, sync_engine, async_session, sync_session = await _build_file_backed_engines(
        tmp_path / "stage_pii.db"
    )
    seed = await _seed(async_session)
    seed.update(sync_session=sync_session, async_session=async_session, tmp_path=tmp_path)
    seed["canal"] = _CanalGravado()
    with (
        patch.object(task_module, "SyncSessionLocal", sync_session),
        patch.object(events_module, "_get_redis", lambda: seed["canal"]),
    ):
        yield seed
    await async_engine.dispose()
    sync_engine.dispose()


def _rodar_loop(seed, run_stage_fn, *, stage: str = _STAGE):
    from backend.app.tasks.pipeline_task import _execute_stages_loop

    ctx = SimpleNamespace(
        artifact_store=None, root=seed["tmp_path"], pipeline_run_id=seed["run_id"]
    )
    return _execute_stages_loop(
        ctx,
        stages=[stage],
        run_id=seed["run_id"],
        ws_id=seed["ws_id"],
        skip_llm=False,
        stop_on_error=True,
        tier="premium",
        llm_stages=set(),
        run_stage_fn=run_stage_fn,
    )


def _rodar_pelo_client_de_producao(seed, runner) -> None:
    """A composição de `run_pipeline_task`: `InProcessPipelineClient` → orchestrator real."""
    from backend.app.services.pipeline.pipeline_client import InProcessPipelineClient

    client = InProcessPipelineClient()
    with patch("pipeline.orchestrator._get_stage_runner", return_value=runner):
        _rodar_loop(seed, lambda c, s: client.execute_stage(c, s, workspace_id=seed["ws_id"]))


def _stage_log(seed) -> PipelineStageLog:
    with seed["sync_session"]() as db:
        stmt = select(PipelineStageLog).where(PipelineStageLog.pipeline_run_id == seed["run_id"])
        return db.execute(stmt).scalars().one()


def _superficies(seed) -> dict[str, str]:
    """Todo texto que a falha deixou em repouso (DB) ou em trânsito (canal do WS)."""
    log = _stage_log(seed)
    return {
        "stage_log.errors": log.errors or "",
        "stage_log.output_summary": json.dumps(log.output_summary or {}, ensure_ascii=False),
        "canal_ws": "\n".join(seed["canal"].mensagens),
    }


def _vazamentos(superficies: dict[str, str]) -> dict[str, list[str]]:
    achados = {nome: [v for v in _VALORES if v in texto] for nome, texto in superficies.items()}
    return {nome: valores for nome, valores in achados.items() if valores}


def test_erro_de_banco_engolido_pelo_orchestrator_nao_publica_o_valor(seeded):
    """Caminho de produção: o orchestrator converte a exceção em `StageResult.error`."""
    _rodar_pelo_client_de_producao(seeded, _quebra_no_banco)

    superficies = _superficies(seeded)
    assert not (vaz := _vazamentos(superficies)), f"valor do banco vazou em {vaz}"
    # Não-vácuo: a falha foi registrada e publicada, e o diagnóstico sobrevive por tipo.
    assert "IntegrityError" in superficies["stage_log.errors"]
    assert '"stage_failed"' in superficies["canal_ws"]


def test_detail_do_driver_nao_publica_a_chave(seeded):
    """Mesmo com os parâmetros escondidos, o DETAIL do Postgres traz `Key (...)=(valores)`."""

    def _runner(_ctx):
        raise _unique_violation_com_detail()

    _rodar_pelo_client_de_producao(seeded, _runner)

    superficies = _superficies(seeded)
    assert not (vaz := _vazamentos(superficies)), f"valor do banco vazou em {vaz}"
    assert "UniqueViolation" in superficies["stage_log.errors"]
    assert "23505" in superficies["stage_log.errors"]


def test_erro_de_banco_que_escapa_do_client_nao_vaza_pelo_traceback(seeded):
    """Caminho de `_run_stage_with_retry` → `_record_stage_exception` (errors + traceback)."""

    def _levanta_do_client(ctx, _stage):
        _quebra_no_banco(ctx)

    _rodar_loop(seeded, _levanta_do_client)

    superficies = _superficies(seeded)
    assert not (vaz := _vazamentos(superficies)), f"valor do banco vazou em {vaz}"
    traceback_txt = _stage_log(seeded).output_summary["traceback"]
    # Não-vácuo: os frames continuam lá — a linha que quebrou segue localizável.
    assert "_quebra_no_banco" in traceback_txt
    assert "IntegrityError" in traceback_txt


def test_retry_continua_casando_o_texto_cru_do_driver(seeded):
    """Redigir o que é gravado não pode cegar o retry: `connection` segue retentando."""
    import backend.app.tasks.pipeline_task as task_module

    def _cai_a_conexao(_ctx, _stage):
        raise _queda_de_conexao()

    with patch.object(task_module.time, "sleep"):
        _rodar_loop(seeded, _cai_a_conexao, stage="extract_members")

    superficies = _superficies(seeded)
    assert not (vaz := _vazamentos(superficies)), f"valor do banco vazou em {vaz}"
    # `extract_members`: max_retries=2 com `connection` na tabela (retry_config.py).
    assert _stage_log(seeded).output_summary["attempt_count"] == 3


def _marca_stage_em_execucao(seed) -> None:
    """Estado em que o worker morre: run com `current_stage` e stage_log `running`."""
    with seed["sync_session"]() as db:
        db.get(PipelineRun, seed["run_id"]).current_stage = _STAGE
        db.add(
            PipelineStageLog(
                id=str(uuid.uuid4()),
                pipeline_run_id=seed["run_id"],
                stage=_STAGE,
                status=PipelineStageStatus.running,
            )
        )
        db.commit()


def test_crash_da_task_nao_grava_o_valor_no_stage_log(seeded):
    """`_on_pipeline_task_failure` grava `Task crashed: {exc}` no stage em execução."""
    import backend.app.tasks.pipeline_task as task_module

    _marca_stage_em_execucao(seeded)
    exc = _unique_violation_com_detail()
    task_module._on_pipeline_task_failure(
        None, exc, "task-id", (), {"run_id": seeded["run_id"]}, None
    )

    log = _stage_log(seeded)
    assert log.status == PipelineStageStatus.failed
    assert log.errors.startswith("Task crashed:")
    assert not [v for v in _VALORES if v in log.errors], log.errors
    assert "UniqueViolation" in log.errors
