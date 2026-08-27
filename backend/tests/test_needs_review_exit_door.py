"""A pausa tem porta de saída, e a porta é a rota — não a constante (ADR-417 · A40.l87).

Por que testes de ENDPOINT e não só de constante: a guarda do cancel é duplicada
(`cancel_run.py` e `pipeline_service.py`) e a A40.l27 mediu que alargar só um lado deixa
o endpoint respondendo 409 com o teste de service verde. O teste de tabela pega o
*próximo* estado; o de endpoint pega o bug de hoje — e é o que teria pego o botão morto
do `NeedsReviewCard`, vivo desde 2026-04-21.
"""

import logging
from contextlib import contextmanager
from unittest.mock import patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.audit_log import AuditLog
from backend.app.models.pipeline_run import PipelineRun, PipelineRunStatus
from backend.app.models.stage_review import StageReview, StageReviewStatus
from backend.app.services.audit import READ_ACCESS_ACTIONS, AuditAction
from backend.app.services.pipeline.dispatch_contract import (
    CANCELLABLE_STATUSES,
    EXECUTOR_VIVO_STATUSES,
    RUN_EXIT_BY_STATUS,
    TERMINAL_STATUSES,
    RunExit,
    discarded_at_review,
)

_CANCEL = "backend.app.application.pipeline_run.cancel_run.cancel_pipeline_run"

ESCAPAVEIS = [
    PipelineRunStatus.pending,
    PipelineRunStatus.running,
    PipelineRunStatus.resuming,
    PipelineRunStatus.needs_review,
]


@contextmanager
def _capture_review_logger():
    """Mesmo isolamento de `test_pipeline_review`: alembic fileConfig cala loggers."""
    target = logging.getLogger("mathoms.pipeline.review")
    prev = (target.level, target.propagate, target.disabled)
    target.setLevel(logging.INFO)
    target.propagate = True
    target.disabled = False
    try:
        yield
    finally:
        target.setLevel(prev[0])
        target.propagate = prev[1]
        target.disabled = prev[2]


async def _run_pausado(db: AsyncSession, ws_id: str, *, stage: str = "analyze_finances") -> str:
    run = PipelineRun(
        workspace_id=ws_id,
        status=PipelineRunStatus.needs_review,
        tier_at_run="premium",
        paused_at_stage=stage,
    )
    db.add(run)
    await db.flush()
    db.add(StageReview(pipeline_run_id=run.id, stage=stage, status=StageReviewStatus.pending))
    await db.commit()
    return run.id


async def _audit_de_cancelamento(db: AsyncSession, run_id: str) -> list[AuditLog]:
    stmt = select(AuditLog).where(
        AuditLog.action == AuditAction.pipeline_run_cancel.value,
        AuditLog.resource_id == run_id,
    )
    return list((await db.execute(stmt)).scalars().all())


async def _pares_run_review(db: AsyncSession) -> list[tuple]:
    db.expire_all()
    stmt = select(PipelineRun.status, StageReview.status).join(
        StageReview, StageReview.pipeline_run_id == PipelineRun.id
    )
    return list((await db.execute(stmt)).all())


async def _review_do_run(db: AsyncSession, run_id: str) -> StageReview:
    db.expire_all()
    stmt = select(StageReview).where(StageReview.pipeline_run_id == run_id)
    return (await db.execute(stmt)).scalar_one()


async def _reler(db: AsyncSession, run_id: str) -> PipelineRun:
    """O service commita por sessão SÍNCRONA — sem expirar, a async devolve o valor velho."""
    db.expire_all()
    return (await db.execute(select(PipelineRun).where(PipelineRun.id == run_id))).scalar_one()


# ── D7: a tabela de saídas cobre o enum, e falha por AUSÊNCIA ──────────────────


def test_todo_estado_declara_como_sai() -> None:
    """Membro novo em `PipelineRunStatus` sem entrada aqui reprova — foi assim que
    `resuming` (A40.l27) e depois `needs_review` (A40.l87) nasceram sem porta."""
    assert set(RUN_EXIT_BY_STATUS) == set(PipelineRunStatus)
    assert all(saidas for saidas in RUN_EXIT_BY_STATUS.values())


def test_cancelavel_e_exatamente_quem_declara_saida_manual() -> None:
    declaram = {st for st, saidas in RUN_EXIT_BY_STATUS.items() if RunExit.manual_cancel in saidas}
    assert declaram == set(CANCELLABLE_STATUSES)


def test_terminal_na_tabela_bate_com_a_tupla_terminal() -> None:
    na_tabela = {st for st, saidas in RUN_EXIT_BY_STATUS.items() if RunExit.terminal in saidas}
    assert na_tabela == set(TERMINAL_STATUSES)
    assert not set(TERMINAL_STATUSES) & set(CANCELLABLE_STATUSES)


def test_audit_do_descarte_sobrevive_ao_purge_de_leitura() -> None:
    """Mutação, não leitura (ADR-275 D5): entrar em READ_ACCESS_ACTIONS apagaria em 365d
    o único registro de QUEM abandonou o run."""
    assert AuditAction.pipeline_run_cancel.value not in READ_ACCESS_ACTIONS


# ── D1: a rota encerra a pausa, e o discriminador sobrevive ────────────────────


@pytest.mark.asyncio
async def test_cancel_pela_rota_encerra_a_pausa(auth_client: AsyncClient, db: AsyncSession):
    """O caso de 2026-08-25, pela API: sem mock do service — o que prova o flip é o DB."""
    ws_id = auth_client.ws_id
    run_id = await _run_pausado(db, ws_id)

    resp = await auth_client.post(f"/api/workspaces/{ws_id}/pipeline/runs/{run_id}/cancel")

    assert resp.status_code == 200
    assert "descartado" in resp.json()["detail"].lower()
    run = await _reler(db, run_id)
    assert run.status == PipelineRunStatus.cancelled
    assert run.completed_at is not None
    # D4 — `paused_at_stage` sobrevive: é ele que discrimina descarte de interrupção.
    assert run.paused_at_stage == "analyze_finances"


@pytest.mark.asyncio
@pytest.mark.parametrize("status", ESCAPAVEIS, ids=lambda s: s.value)
async def test_todo_estado_escapavel_sai_pela_rota(
    auth_client: AsyncClient, db: AsyncSession, status: PipelineRunStatus
):
    """Um por estado, pelo ENDPOINT: a constante sozinha não prova que a rota abriu."""
    ws_id = auth_client.ws_id
    run = PipelineRun(workspace_id=ws_id, status=status, tier_at_run="free")
    db.add(run)
    await db.commit()

    resp = await auth_client.post(f"/api/workspaces/{ws_id}/pipeline/runs/{run.id}/cancel")

    assert resp.status_code == 200, resp.text
    depois = await _reler(db, run.id)
    assert depois.status in TERMINAL_STATUSES
    # ADR-417 D4 — o writer tem de cobrir TODO estado escapável; esquecer um novo
    # reprova aqui, pelo mesmo mecanismo de ausência do `RUN_EXIT_BY_STATUS`.
    assert depois.cancelled_from_status == status.value


@pytest.mark.asyncio
async def test_run_interrompido_mantem_a_copy_de_interrupcao(
    auth_client: AsyncClient, db: AsyncSession
):
    """O `detail` é decidido pelo status lido ANTES do flip — leitura de estado vivo, não
    de resíduo. É por isso que ele sobrevive à queda do discriminador derivado."""
    ws_id = auth_client.ws_id
    run = PipelineRun(workspace_id=ws_id, status=PipelineRunStatus.running, tier_at_run="free")
    db.add(run)
    await db.commit()

    resp = await auth_client.post(f"/api/workspaces/{ws_id}/pipeline/runs/{run.id}/cancel")

    assert resp.status_code == 200
    assert "parará" in resp.json()["detail"]
    assert (await _reler(db, run.id)).status == PipelineRunStatus.cancelled


@pytest.mark.asyncio
async def test_audit_registra_quem_descartou_e_o_que_ficou(
    auth_client: AsyncClient, db: AsyncSession
):
    ws_id = auth_client.ws_id
    run_id = await _run_pausado(db, ws_id)

    await auth_client.post(f"/api/workspaces/{ws_id}/pipeline/runs/{run_id}/cancel")

    rows = await _audit_de_cancelamento(db, run_id)
    assert len(rows) == 1
    assert rows[0].actor_user_id is not None
    assert rows[0].details["previous_status"] == "needs_review"
    assert rows[0].details["paused_at_stage"] == "analyze_finances"
    assert rows[0].details["pending_reviews"] == 1


# ── D3: o resíduo é sancionado, e não morde o predicado da A40.l84 ────────────


@pytest.mark.asyncio
async def test_review_pendente_sobrevive_ao_descarte_sem_virar_outro_status(
    auth_client: AsyncClient, db: AsyncSession
):
    """`(cancelled, pending)` é resíduo SANCIONADO: nada se apaga, nada muda de status.
    O predicado de fecho da A40.l84 é `(completed, pending)` — escrito como "terminal +
    pending" mordia isto aqui e as duas lanes se refutariam."""
    ws_id = auth_client.ws_id
    run_id = await _run_pausado(db, ws_id)

    await auth_client.post(f"/api/workspaces/{ws_id}/pipeline/runs/{run_id}/cancel")

    pares = await _pares_run_review(db)
    assert (PipelineRunStatus.cancelled, StageReviewStatus.pending) in pares
    assert (PipelineRunStatus.completed, StageReviewStatus.pending) not in pares


# ── D2 §Corolário: run terminal não aceita mais conferência ───────────────────


@pytest.mark.asyncio
async def test_action_review_recusa_run_terminal_sem_emitir_telemetria(
    auth_client: AsyncClient, db: AsyncSession, caplog: pytest.LogCaptureFixture
):
    """Aprovar review de run morto mutava filho de run terminal E poluía o KR1 da A29.l1
    com decisões sobre runs que ninguém vai retomar. A telemetria é o dano silencioso."""
    ws_id = auth_client.ws_id
    run_id = await _run_pausado(db, ws_id)
    review_id = (await _review_do_run(db, run_id)).id
    await auth_client.post(f"/api/workspaces/{ws_id}/pipeline/runs/{run_id}/cancel")

    with _capture_review_logger(), caplog.at_level("INFO", logger="mathoms.pipeline.review"):
        resp = await auth_client.post(
            f"/api/workspaces/{ws_id}/pipeline/runs/{run_id}/reviews/{review_id}",
            json={"action": "approve"},
        )

    assert resp.status_code == 409
    assert not [r for r in caplog.records if r.getMessage() == "review_action"]
    review = await _review_do_run(db, run_id)
    assert review.status == StageReviewStatus.pending


@pytest.mark.asyncio
async def test_flip_no_op_do_service_vira_conflito_nao_sucesso(
    auth_client: AsyncClient, db: AsyncSession
):
    """O retorno de `cancel_pipeline_run` era DESCARTADO: corrida respondia 200 sobre nada
    feito. Mesma classe de compensação silenciosa que a ADR-359 loga como no-op."""
    ws_id = auth_client.ws_id
    run_id = await _run_pausado(db, ws_id)
    # Mesma string de `test_pipeline_api._CANCEL`: o `__init__` do pacote re-exporta a
    # função com o nome do módulo, e só `mock.patch` resolve o prefixo como módulo.
    with patch(_CANCEL, return_value=False):
        resp = await auth_client.post(f"/api/workspaces/{ws_id}/pipeline/runs/{run_id}/cancel")

    assert resp.status_code == 409
    assert (await _reler(db, run_id)).status == PipelineRunStatus.needs_review


# ── D4 (PR2): o estado terminal é GRAVADO, e por isso discrimina ──────────────


@pytest.mark.asyncio
async def test_descarte_grava_o_estado_do_instante_terminal(
    auth_client: AsyncClient, db: AsyncSession
):
    ws_id = auth_client.ws_id
    run_id = await _run_pausado(db, ws_id)

    await auth_client.post(f"/api/workspaces/{ws_id}/pipeline/runs/{run_id}/cancel")

    assert discarded_at_review((await _reler(db, run_id)).cancelled_from_status)


# O caso que refutou a derivacao por `paused_at_stage`: quem pausou, conferiu, RETOMOU
# e so entao foi interrompido tem `paused_at_stage` preenchido (ninguem o zera) e NAO e
# descarte. O `xfail(strict=True)` que marcava esta lacuna sai junto com o fix.
@pytest.mark.asyncio
async def test_retomado_e_depois_interrompido_nao_le_como_descarte(
    auth_client: AsyncClient, db: AsyncSession
):
    ws_id = auth_client.ws_id
    run = PipelineRun(
        workspace_id=ws_id,
        status=PipelineRunStatus.running,
        tier_at_run="premium",
        paused_at_stage="analyze_finances",  # resíduo da pausa já conferida e retomada
    )
    db.add(run)
    await db.commit()

    await auth_client.post(f"/api/workspaces/{ws_id}/pipeline/runs/{run.id}/cancel")

    depois = await _reler(db, run.id)
    assert depois.paused_at_stage == "analyze_finances"
    assert not discarded_at_review(depois.cancelled_from_status)


@pytest.mark.asyncio
async def test_row_legada_sem_coluna_e_desconhecida_nao_interrompida(
    auth_client: AsyncClient, db: AsyncSession
):
    """`None` nunca vira afirmação: run anterior à coluna não recebe rótulo nenhum."""
    ws_id = auth_client.ws_id
    run = PipelineRun(
        workspace_id=ws_id,
        status=PipelineRunStatus.cancelled,
        tier_at_run="free",
        paused_at_stage="analyze_finances",
        cancelled_from_status=None,
    )
    db.add(run)
    await db.commit()

    assert not discarded_at_review((await _reler(db, run.id)).cancelled_from_status)


# ── D5: a pausa bloqueia disparo novo, e o resume recusa executor concorrente ──


@pytest.mark.asyncio
async def test_trigger_sobre_pausa_viva_recusa_nomeando_a_saida(
    auth_client_with_doc: AsyncClient, db: AsyncSession
):
    """Antes, disparar por cima era silencioso E destrutivo: a pausa nunca mais seria
    retomada e as `stage_reviews` dela ficavam `pending` órfãs, sem varredura."""
    auth_client = auth_client_with_doc
    ws_id = auth_client.ws_id
    run_id = await _run_pausado(db, ws_id)

    resp = await auth_client.post(f"/api/workspaces/{ws_id}/pipeline/run", json={})

    assert resp.status_code == 409
    detalhe = resp.json()["detail"]
    assert "pausado" in detalhe.lower()
    assert "descarte" in detalhe.lower()  # nomeia a saída, nunca "aguarde"
    assert run_id[:8] in detalhe


@pytest.mark.asyncio
async def test_resume_recusa_quando_outro_executor_esta_vivo(
    auth_client: AsyncClient, db: AsyncSession
):
    """Fecha o executor duplo: a pausa é invisível ao índice parcial, então a guarda
    tem de morar no instante em que a pretensão a executor é exercida."""
    from backend.app.services.pipeline.pipeline_service import resume_pipeline_run

    ws_id = auth_client.ws_id
    pausado = await _run_pausado(db, ws_id)
    db.add(PipelineRun(workspace_id=ws_id, status=PipelineRunStatus.running, tier_at_run="free"))
    await db.commit()

    with pytest.raises(ValueError, match="ativa"):
        resume_pipeline_run(pausado, ws_id)

    assert (await _reler(db, pausado)).status == PipelineRunStatus.needs_review


def test_executor_vivo_nao_inclui_a_pausa() -> None:
    """A pausa não segura executor — ela é uma PRETENSÃO a virar um. Incluí-la aqui
    faria a guarda do resume recusar o próprio run que está retomando."""
    assert PipelineRunStatus.needs_review not in EXECUTOR_VIVO_STATUSES
    assert set(EXECUTOR_VIVO_STATUSES) < set(CANCELLABLE_STATUSES)


# ── A40.l84: a retomada exige decisão registrada em TODA entrada ──────────────


@pytest.mark.asyncio
async def test_resume_pelo_service_recusa_review_sem_decisao(
    auth_client: AsyncClient, db: AsyncSession
):
    """RV8-08: o predicado vivia só no use case HTTP e o service era caminho vivo — dois
    runs de dogfood completaram sobre review que ninguém aprovou."""
    from backend.app.services.pipeline.pipeline_service import resume_pipeline_run

    ws_id = auth_client.ws_id
    run_id = await _run_pausado(db, ws_id)

    # `match` no nome do stage: `PipelineDispatchError` é `RuntimeError`, então sem o
    # guard o teste fica vermelho por não levantar `ValueError`; e o nome do stage prova
    # que a mensagem é a DESTE predicado, não a da guarda de executor concorrente.
    with pytest.raises(ValueError, match="analyze_finances"):
        resume_pipeline_run(run_id, ws_id)

    run = await _reler(db, run_id)
    assert run.status == PipelineRunStatus.needs_review  # nem `resuming`, nem `failed`
    assert run.paused_at_stage == "analyze_finances"  # ADR-359 §2: não houve forward
    assert (await _review_do_run(db, run_id)).status == StageReviewStatus.pending


@pytest.mark.asyncio
async def test_review_edited_destrava_a_retomada(auth_client: AsyncClient, db: AsyncSession):
    """O predicado é `NOT IN (approved, edited)`: editar É decidir. Escrito como
    `== pending`, membro novo do enum destravaria calado (ADR-417 D3)."""
    ws_id = auth_client.ws_id
    run_id = await _run_pausado(db, ws_id)
    review = await _review_do_run(db, run_id)
    review.status = StageReviewStatus.edited
    await db.commit()

    with patch("backend.app.services.pipeline.pipeline_service._dispatch_resume") as dispatch:
        resp = await auth_client.post(f"/api/workspaces/{ws_id}/pipeline/runs/{run_id}/resume")

    assert resp.status_code == 202
    dispatch.assert_called_once()
    assert (await _reler(db, run_id)).status == PipelineRunStatus.resuming


# Camada em `_mark_run_completed`, o único escritor de `completed` sem filtro algum.
# Levantar sobre `resuming` + `celery_task_id IS NULL` entregaria o run ao ceifador de
# órfãos, que grava `failed`/DISPATCH_UNCONFIRMED — compensar é REVERTER (ADR-359 §2). O
# guard de entrada torna este ramo inalcançável pelo caller; a chamada direta é o único
# caminho de teste, e guard sem caminho de teste não conta para o fecho.
@pytest.mark.asyncio
async def test_fecho_do_resume_reverte_a_pausa_antes_de_levantar(
    auth_client: AsyncClient, db: AsyncSession
):
    from backend.app.services.pipeline.pipeline_service import _mark_run_completed

    ws_id = auth_client.ws_id
    run_id = await _run_pausado(db, ws_id)
    run = await _reler(db, run_id)
    run.status = PipelineRunStatus.resuming
    await db.commit()

    with pytest.raises(ValueError, match="analyze_finances"):
        _mark_run_completed(run_id, "analyze_finances")

    depois = await _reler(db, run_id)
    assert depois.status == PipelineRunStatus.needs_review
    assert depois.paused_at_stage == "analyze_finances"  # nunca NULL (A40.l27)
    assert (PipelineRunStatus.completed, StageReviewStatus.pending) not in await _pares_run_review(
        db
    )
