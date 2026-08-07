"""A40.l18 · ADR-357 — add-on advisory que não entrega degrada o run, não o destrói."""

# Incidente de origem: run `2ded7aab` marcado `failed` com o E5 completo em
# `pipeline_artifacts` (123.498 bytes). O relatório era derivável e não foi
# derivado, porque `success: False` de um add-on da cauda era indistinguível de
# "o pipeline não pode continuar".
#
# Estes testes exercitam o LOOP REAL (`_execute_stages_loop`) e o finalize real,
# com fakes de stage — não os helpers de gravação isoladamente. Um teste que
# chame `_record_stage_result` direto provaria o mapeamento de status e não a
# disposição.

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import patch

import pytest
import pytest_asyncio
from sqlalchemy import select

from backend.app.core.security import hash_password
from backend.app.models.pipeline_artifact import PipelineArtifact
from backend.app.models.pipeline_run import (
    PipelineRun,
    PipelineRunStatus,
    PipelineStageLog,
    PipelineStageStatus,
)
from backend.app.models.report import Report
from backend.app.models.stage_review import StageReview
from backend.app.models.user import User
from backend.app.models.workspace import Workspace
from backend.tests.test_pipeline_task import _build_file_backed_engines
from pipeline.orchestrator import StageResult

_E5_STAGE = "analyze_finances"
_E5_KEY = "analise_financeira"
_PARECER = "review_finances_holistic"
_NARRATIVAS = "generate_narratives"
_CROSSVAL = "validate_cross"

_E5_PAYLOAD = {"score": {"valor": 7, "classificacao": "Bom"}, "periodo_dados": "2026-01"}


class _ScriptedStages:
    """Fake de execução: por stage, entrega / não entrega / levanta / pausa."""

    def __init__(self, *, not_delivered=(), raises=(), invalid_validation=()):
        self.calls: list[str] = []
        self._not_delivered = set(not_delivered)
        self._raises = set(raises)
        self._invalid = set(invalid_validation)

    def __call__(self, ctx, stage):
        self.calls.append(stage)
        if stage in self._raises:
            raise RuntimeError(f"provider caiu em {stage}")
        if stage == _E5_STAGE:
            ctx.artifact_store.write(_E5_STAGE, _E5_KEY, dict(_E5_PAYLOAD))
        if stage in self._not_delivered:
            return StageResult(stage=stage, success=False, duration_ms=1.0, detail=None)
        if stage in self._invalid:
            detail = {"validation": {"valid": False, "errors": ["[CV3] conservação"]}}
            return StageResult(stage=stage, success=True, duration_ms=1.0, detail=detail)
        return StageResult(stage=stage, success=True, duration_ms=1.0, detail={"ok": True})

    def count_for(self, stage: str) -> int:
        return sum(1 for s in self.calls if s == stage)


async def _seed(async_session_factory, *, base_run_id=None) -> dict:
    async with async_session_factory() as session:
        user = User(
            id=str(uuid.uuid4()),
            email=f"degr_{uuid.uuid4().hex[:6]}@test.com",
            hashed_password=hash_password("pass"),
            full_name="DegradeTest",
        )
        ws = Workspace(id=str(uuid.uuid4()), owner_id=user.id, name="WS")
        run = PipelineRun(
            id=str(uuid.uuid4()),
            workspace_id=ws.id,
            status=PipelineRunStatus.running,
            base_run_id=base_run_id,
        )
        session.add_all([user, ws, run])
        await session.commit()
        return {"ws_id": ws.id, "run_id": run.id}


@pytest_asyncio.fixture
async def seeded(tmp_path):
    import backend.app.tasks.pipeline_task as task_module

    async_engine, sync_engine, async_session, sync_session = await _build_file_backed_engines(
        tmp_path / "degradation.db"
    )
    seed = await _seed(async_session)
    seed["async_session"] = async_session
    seed["tmp_path"] = tmp_path
    with patch.object(task_module, "SyncSessionLocal", sync_session):
        yield seed
    await async_engine.dispose()
    sync_engine.dispose()


def _drive(seed, stage_fn, *, stages, stop_on_error=True):
    """Roda o loop e o finalize — o caminho que produz o desfecho terminal."""
    from backend.app.tasks.pipeline_task import (
        _execute_stages_loop,
        _finalize_pipeline_outcome,
    )

    has_failure, paused = _execute_stages_loop(
        SimpleNamespace(artifact_store=None),
        stages=stages,
        run_id=seed["run_id"],
        ws_id=seed["ws_id"],
        skip_llm=False,
        stop_on_error=stop_on_error,
        tier="premium",
        llm_stages=set(),
        run_stage_fn=stage_fn,
    )
    _finalize_pipeline_outcome(seed["run_id"], seed["ws_id"], seed["tmp_path"], has_failure, paused)
    return has_failure, paused


async def _run_row(seed) -> PipelineRun:
    async with seed["async_session"]() as s:
        return await s.get(PipelineRun, seed["run_id"])


async def _stage_status(seed, stage: str) -> PipelineStageStatus | None:
    async with seed["async_session"]() as s:
        row = (
            await s.execute(
                select(PipelineStageLog).where(
                    PipelineStageLog.pipeline_run_id == seed["run_id"],
                    PipelineStageLog.stage == stage,
                )
            )
        ).scalar_one_or_none()
        return row.status if row else None


async def _stage_log_count(seed, stage: str) -> int:
    async with seed["async_session"]() as s:
        rows = await s.execute(
            select(PipelineStageLog.id).where(
                PipelineStageLog.pipeline_run_id == seed["run_id"],
                PipelineStageLog.stage == stage,
            )
        )
        return len(list(rows))


async def _reports(seed) -> list[Report]:
    async with seed["async_session"]() as s:
        return list(
            (await s.execute(select(Report).where(Report.workspace_id == seed["ws_id"])))
            .scalars()
            .all()
        )


async def _stage_reviews(seed) -> list[StageReview]:
    async with seed["async_session"]() as s:
        return list(
            (
                await s.execute(
                    select(StageReview).where(StageReview.pipeline_run_id == seed["run_id"])
                )
            )
            .scalars()
            .all()
        )


# ─────────────────── a disposição: degradável vs. required ───────────────────


@pytest.mark.asyncio
async def test_degradavel_que_nao_entrega_produz_partial_failure_com_relatorio(seeded):
    """O caso do incidente: o parecer não entrega e o relatório É derivado."""
    stages = _ScriptedStages(not_delivered={_PARECER})
    _drive(seeded, stages, stages=[_E5_STAGE, _PARECER])

    run = await _run_row(seeded)
    assert run.status is PipelineRunStatus.partial_failure
    assert await _stage_status(seeded, _PARECER) is PipelineStageStatus.degraded
    # ADR-357 §3 — campo de falha preenchido ao lado de status entregue mentiria.
    assert run.failed_at_stage is None

    reports = await _reports(seeded)
    assert len(reports) == 1, "post-processing precisa rodar em degradação (ADR-357 §5)"
    assert reports[0].analysis_artifact_id is not None, "FK para o artifact E5 (ADR-131)"


@pytest.mark.asyncio
async def test_required_que_nao_entrega_continua_falhando_o_run(seeded):
    """Comportamento atual preservado: a cabeça do pipeline veta o entregável."""
    stages = _ScriptedStages(not_delivered={_E5_STAGE})
    _drive(seeded, stages, stages=[_E5_STAGE, _PARECER])

    run = await _run_row(seeded)
    assert run.status is PipelineRunStatus.failed
    assert run.failed_at_stage == _E5_STAGE
    assert await _reports(seeded) == []


@pytest.mark.asyncio
async def test_disposicao_e_cega_a_forma_da_nao_entrega(seeded):
    """Exceção que esgota os retries degrada igual a `success: False` (ADR-357 §2)."""
    # `result.error` é proibido como discriminador: a mesma falha de rede cai dos
    # dois lados conforme a linha em que estoura.
    stages = _ScriptedStages(raises={_PARECER})
    _drive(seeded, stages, stages=[_E5_STAGE, _PARECER])

    run = await _run_row(seeded)
    assert run.status is PipelineRunStatus.partial_failure
    assert await _stage_status(seeded, _PARECER) is PipelineStageStatus.degraded
    assert run.failed_at_stage is None
    assert len(await _reports(seeded)) == 1


# ─────────────── degradação não pode cascatear pela cauda ───────────────


@pytest.mark.asyncio
async def test_degradacao_nao_honra_stop_on_error(seeded):
    """Degradar o 1º da cauda não pode apagar os outros dois."""
    # Os 3 degradáveis são os 3 ÚLTIMOS de FULL_ORDER e o default do
    # trigger/resume é `stop_on_error=True`. Se a degradação parasse o loop, o
    # cliente premium perderia o parecer que pagou — uma lacuna virando três.
    stages = _ScriptedStages(not_delivered={_NARRATIVAS})
    _drive(
        seeded,
        stages,
        stages=[_E5_STAGE, _NARRATIVAS, _CROSSVAL, _PARECER],
        stop_on_error=True,
    )

    assert stages.count_for(_CROSSVAL) == 1, "validate_cross tem de rodar"
    assert stages.count_for(_PARECER) == 1, "o parecer pago tem de rodar"
    run = await _run_row(seeded)
    assert run.status is PipelineRunStatus.partial_failure
    assert await _stage_status(seeded, _NARRATIVAS) is PipelineStageStatus.degraded
    assert await _stage_status(seeded, _CROSSVAL) is PipelineStageStatus.completed
    assert await _stage_status(seeded, _PARECER) is PipelineStageStatus.completed


@pytest.mark.asyncio
async def test_required_que_falha_ainda_para_o_loop(seeded):
    """O `stop_on_error` continua valendo para não-entrega de stage required."""
    stages = _ScriptedStages(not_delivered={_E5_STAGE})
    _drive(seeded, stages, stages=[_E5_STAGE, _PARECER], stop_on_error=True)
    assert stages.count_for(_PARECER) == 0


# ─────────────── redelivery não re-paga o stage degradado ───────────────


@pytest.mark.asyncio
async def test_redelivery_de_stage_degradado_nao_re_executa(seeded):
    """`degraded` em `_STAGE_DONE_STATUSES` — a linha mais importante do PR."""
    # Sem ela, o redelivery Celery re-executa e re-paga a call LLM já cobrada
    # (US$ 0,48 no incidente), reintroduzindo no ramo degradado a regressão que a
    # A37.l12 fechou.
    stages = _ScriptedStages(not_delivered={_PARECER})
    _drive(seeded, stages, stages=[_E5_STAGE, _PARECER])
    assert stages.count_for(_PARECER) == 1

    _drive(seeded, stages, stages=[_E5_STAGE, _PARECER])
    assert stages.count_for(_PARECER) == 1, "redelivery re-pagou o stage degradado"

    assert await _stage_log_count(seeded, _PARECER) == 1, "redelivery duplicou stage_log"


# ─────────────── o canal `validation` é ortogonal à criticidade ───────────────


@pytest.mark.asyncio
async def test_degradavel_com_veredito_invalido_ainda_pausa(seeded):
    """`criticality` alcança só a NÃO-ENTREGA; veredito entregue continua pausando."""
    # Invertido em 2026-08-06 por co-design: a forma anterior do critério de
    # aceite mandava degradar aqui, o que teria apagado o único gate de pausa por
    # violação de conservação do produto — publicando à família um relatório cujos
    # números não fecham, com banner de ressalva.
    stages = _ScriptedStages(invalid_validation={_CROSSVAL})
    _drive(seeded, stages, stages=[_E5_STAGE, _CROSSVAL])

    run = await _run_row(seeded)
    assert run.status is PipelineRunStatus.needs_review
    assert run.paused_at_stage == _CROSSVAL
    assert await _stage_status(seeded, _CROSSVAL) is PipelineStageStatus.needs_review
    assert len(await _stage_reviews(seeded)) == 1


@pytest.mark.asyncio
async def test_gate_espelhado_nao_entrega_nao_cria_stage_review(seeded):
    """O espelho do teste acima: não-entrega degrada e NÃO pausa."""
    stages = _ScriptedStages(not_delivered={_CROSSVAL})
    _drive(seeded, stages, stages=[_E5_STAGE, _CROSSVAL])

    run = await _run_row(seeded)
    assert run.status is PipelineRunStatus.partial_failure
    assert run.paused_at_stage is None
    assert await _stage_status(seeded, _CROSSVAL) is PipelineStageStatus.degraded
    assert await _stage_reviews(seeded) == []


# ─────────────── `partial_failure` exige entregável ───────────────


@pytest.mark.asyncio
async def test_degradado_sem_e5_vira_failed(seeded):
    """Sem artifact E5 não há relatório — `partial_failure` mentiria."""
    # A cegueira da §2 é sobre a forma da não-entrega do STAGE. "O run entregou?"
    # é pergunta de run, respondida por evidência.
    stages = _ScriptedStages(not_delivered={_PARECER})
    _drive(seeded, stages, stages=[_PARECER])

    run = await _run_row(seeded)
    assert run.status is PipelineRunStatus.failed
    assert await _stage_status(seeded, _PARECER) is PipelineStageStatus.degraded
    assert await _reports(seeded) == []


async def _seed_tail_run(async_session, base: dict, tmp_path) -> dict:
    """Run só-de-cauda: `base_run_id` apontando para o base, MESMO workspace."""
    tail = await _seed(async_session, base_run_id=base["run_id"])
    tail.update({"async_session": async_session, "tmp_path": tmp_path})
    async with async_session() as s:
        tail_run = await s.get(PipelineRun, tail["run_id"])
        tail_run.workspace_id = base["ws_id"]
        await s.commit()
    tail["ws_id"] = base["ws_id"]
    return tail


@pytest_asyncio.fixture
async def base_and_tail(tmp_path):
    """Run base com E5 escrito pelo store + run só-de-cauda apontando para ele."""
    # O E5 vem de um run base REAL, não semeado à mão: é o `pipeline_run_id` do
    # artifact que decide se o predicado de entregável alcança o base run.
    import backend.app.tasks.pipeline_task as task_module

    async_engine, sync_engine, async_session, sync_session = await _build_file_backed_engines(
        tmp_path / "base_run.db"
    )
    base = await _seed(async_session)
    base.update({"async_session": async_session, "tmp_path": tmp_path})
    with patch.object(task_module, "SyncSessionLocal", sync_session):
        _drive(base, _ScriptedStages(), stages=[_E5_STAGE])
        yield base, await _seed_tail_run(async_session, base, tmp_path)
    await async_engine.dispose()
    sync_engine.dispose()


@pytest.mark.asyncio
async def test_degradado_com_e5_do_base_run_e_partial_failure(base_and_tail):
    """Run só-de-cauda (`from_stage`) lê o E5 do run BASE — não pode virar `failed`."""
    base, tail = base_and_tail
    assert len(await _reports(base)) == 1

    _drive(tail, _ScriptedStages(not_delivered={_PARECER}), stages=[_PARECER])
    run = await _run_row(tail)
    assert (
        run.status is PipelineRunStatus.partial_failure
    ), "o predicado de entregável precisa alcançar o base run (ADR-291)"
