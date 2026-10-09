"""Prazo do run e o sinal do soft time limit, vistos de `pipeline/` sem importar o Celery."""

from __future__ import annotations

import logging
import sys
import threading
import types

import pytest

from pipeline.observability import StageLogTail
from pipeline.run_deadline import RunDeadline, RunTimeLimitExceededError, time_limit_exceptions


class _Clock:
    def __init__(self, now: float = 100.0) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now


@pytest.fixture
def fake_billiard(monkeypatch):
    """Processo sob o billiard: o módulo do sinal está em `sys.modules`."""
    module = types.ModuleType("billiard.exceptions")

    class SoftTimeLimitExceeded(Exception):
        pass

    module.SoftTimeLimitExceeded = SoftTimeLimitExceeded
    monkeypatch.setitem(sys.modules, "billiard.exceptions", module)
    return SoftTimeLimitExceeded


def test_sem_prazo_nunca_expira():
    deadline = RunDeadline.starting_now(None)

    assert not deadline.expired()
    deadline.check("stage x")


def test_relogio_vence_so_depois_da_carencia():
    clock = _Clock()
    deadline = RunDeadline.starting_now(60, grace_s=5, clock=clock)

    clock.now = 164.9
    assert not deadline.expired()
    clock.now = 165.0
    assert deadline.expired()
    assert deadline.elapsed_s() == 65.0


def test_disparo_vence_o_prazo_antes_do_relogio_para_todas_as_threads():
    clock = _Clock()
    deadline = RunDeadline.starting_now(60, grace_s=5, clock=clock)
    other_thread = threading.Thread(target=deadline.trip)

    other_thread.start()
    other_thread.join()

    assert deadline.expired() and deadline.remaining_s() == 0.0


def test_sem_prazo_o_disparo_ainda_vale():
    deadline = RunDeadline.starting_now(None)

    deadline.trip()

    with pytest.raises(RunTimeLimitExceededError):
        deadline.check("stage x")


def test_check_depois_do_prazo_recusa_o_trabalho_pelo_nome():
    clock = _Clock()
    deadline = RunDeadline.starting_now(5, clock=clock)
    clock.now = 105.0

    with pytest.raises(RunTimeLimitExceededError, match="chamada LLM"):
        deadline.check("chamada LLM")


def test_sem_billiard_carregado_so_o_erro_do_prazo_encerra_o_run(monkeypatch):
    monkeypatch.delitem(sys.modules, "billiard.exceptions", raising=False)

    assert time_limit_exceptions() == (RunTimeLimitExceededError,)


def test_sob_billiard_o_sinal_tambem_encerra_o_run(fake_billiard):
    assert time_limit_exceptions() == (RunTimeLimitExceededError, fake_billiard)


def _runner_raising(monkeypatch, exc: BaseException) -> None:
    from pipeline import orchestrator

    def _raise(_ctx):
        raise exc

    monkeypatch.setattr(orchestrator, "_get_stage_runner", lambda _stage: _raise)


@pytest.mark.parametrize("which", ["sinal", "prazo"])
def test_run_stage_relanca_o_fim_de_prazo_e_restaura_o_processo(
    which, fake_billiard, monkeypatch, tmp_path
):
    from pipeline import orchestrator
    from pipeline.context import WorkspaceContext

    exc = fake_billiard() if which == "sinal" else RunTimeLimitExceededError("prazo")
    _runner_raising(monkeypatch, exc)
    stdout, stderr = sys.stdout, sys.stderr

    with pytest.raises(type(exc)):
        orchestrator._run_stage(WorkspaceContext(root=tmp_path), "reconcile_transactions")

    assert (sys.stdout, sys.stderr) == (stdout, stderr)
    handlers = logging.getLogger("mathoms.pipeline").handlers
    assert not any(isinstance(h, StageLogTail) for h in handlers)


def test_run_stage_segue_achatando_falha_do_stage(fake_billiard, monkeypatch, tmp_path):
    from pipeline import orchestrator
    from pipeline.context import WorkspaceContext

    _runner_raising(monkeypatch, RuntimeError("provider caiu"))

    result = orchestrator._run_stage(WorkspaceContext(root=tmp_path), "reconcile_transactions")

    assert result.success is False and result.error == "provider caiu"
