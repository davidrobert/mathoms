"""A40.l84 — nenhum desfecho que ENTREGA nasce sobre `StageReview` sem decisão."""

# O par `(completed, pending)` do RV8-08: dois runs de dogfood nasceram assim, e um deles
# era o baseline de comparação do outro. O guard de entrada (`_flip_run_to_resuming`) fecha
# a porta; estes testes fecham a CLASSE, no escritor do desfecho.
#
# Harness importado de `test_stage_degradation`: é o único que roda `_execute_stages_loop`
# + `_finalize_run` reais. A review NASCE de pausa real (`invalid_validation`), nunca
# semeada à mão — `_build_file_backed_engines` roda com `PRAGMA foreign_keys = 0`, então
# `pipeline_run_id` inventado passaria calado (ADR-371).
#
# A cauda TEM de ser tail-only com fake limpo. Reusar a mesma lista de stages re-pausa,
# `_finalize_pipeline_outcome` early-returna em `paused` e o teste fica VERDE com zero
# guard — colhendo o desfecho da pausa, não o do fecho.

from __future__ import annotations

from unittest.mock import patch

import pytest

from backend.app.models.pipeline_run import PipelineRun, PipelineRunStatus
from backend.app.models.stage_review import StageReviewStatus
from backend.tests.test_stage_degradation import (
    _CROSSVAL,
    _E5_STAGE,
    _PARECER,
    _drive,
    _reports,
    _run_row,
    _ScriptedStages,
    _stage_reviews,
    seeded,
)

__all__ = ["seeded"]

_TASK = "backend.app.tasks.pipeline_task"


async def _forcar_status(seed, status: PipelineRunStatus) -> None:
    """Estado do redelivery: `_mark_run_started` deixa `needs_review` re-entrar."""
    async with seed["async_session"]() as s:
        run = await s.get(PipelineRun, seed["run_id"])
        run.status = status
        await s.commit()


@pytest.mark.asyncio
async def test_finalize_reestaciona_em_vez_de_entregar_com_review_pendente(seeded):
    """Em `origin/main` este run terminava `completed` com a conferência intocada."""
    _drive(seeded, _ScriptedStages(invalid_validation={_CROSSVAL}), stages=[_E5_STAGE, _CROSSVAL])
    assert len(await _stage_reviews(seeded)) == 1
    await _forcar_status(seeded, PipelineRunStatus.running)

    with patch(f"{_TASK}.publish_run_completed") as publicou:
        _drive(seeded, _ScriptedStages(), stages=[_PARECER])

    run = await _run_row(seeded)
    assert run.status is PipelineRunStatus.needs_review
    assert run.paused_at_stage == _CROSSVAL
    assert await _reports(seeded) == []  # o relatório não nasce sobre output não conferido
    assert (await _stage_reviews(seeded))[0].status is StageReviewStatus.pending
    publicou.assert_not_called()  # o par vazava para o SSE também


@pytest.mark.asyncio
async def test_finalize_grava_failed_mesmo_com_review_pendente(seeded):
    """ESCOPO: o fecho é `(completed, pending)`, nunca "terminal + pending" (ADR-417 D3)."""
    # A pausa é no PRÓPRIO stage que depois falha: `needs_review` não está em
    # `_STAGE_DONE_STATUSES`, então o redelivery o re-executa. Pausar noutro stage faria o
    # marcador pular a re-execução e o teste mediria o ramo `completed`.
    _drive(seeded, _ScriptedStages(invalid_validation={_E5_STAGE}), stages=[_E5_STAGE])
    await _forcar_status(seeded, PipelineRunStatus.running)

    with patch(f"{_TASK}.publish_run_failed") as publicou:
        _drive(seeded, _ScriptedStages(raises={_E5_STAGE}), stages=[_E5_STAGE])

    run = await _run_row(seeded)
    assert run.status is PipelineRunStatus.failed  # reparcar aqui seria o defeito
    assert (await _stage_reviews(seeded))[0].status is StageReviewStatus.pending
    publicou.assert_called_once()


@pytest.mark.asyncio
async def test_cancelado_nao_publica_fim_apos_a_extracao_do_finalize(seeded):
    """A extração de `_commit_run_outcome` tirou o `return` de dentro do bloco `with`."""
    await _forcar_status(seeded, PipelineRunStatus.cancelled)

    with (
        patch(f"{_TASK}.publish_run_completed") as completou,
        patch(f"{_TASK}.publish_run_failed") as falhou,
    ):
        _drive(seeded, _ScriptedStages(), stages=[_E5_STAGE])

    assert (await _run_row(seeded)).status is PipelineRunStatus.cancelled
    completou.assert_not_called()
    falhou.assert_not_called()
