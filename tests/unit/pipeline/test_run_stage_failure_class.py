"""ADR-447 — `_run_stage` grava a classe da exceção capturada no `detail`, nos dois ramos."""

from __future__ import annotations

import logging
import sys
from decimal import Decimal
from types import SimpleNamespace

import pytest

import pipeline.orchestrator as orchestrator
from pipeline.llm.call_hooks import LLMBudgetExceededError
from pipeline.stage_failure_reason import FAILURE_CLASS_KEY


def _raising(exc: BaseException):
    def _runner(_ctx):
        raise exc

    return _runner


def _exiting(code: int):
    def _runner(_ctx):
        print("[ERROR] arquivo de entrada ausente", file=sys.stderr)
        sys.exit(code)

    return _runner


def _run_leaf(monkeypatch, tmp_path, runner):
    monkeypatch.setattr(orchestrator, "_get_stage_runner", lambda _stage: runner)
    ctx = SimpleNamespace(root=tmp_path, pipeline_run_id="run")
    return orchestrator._run_stage(ctx, "extract_members")


@pytest.fixture
def tail_vazio():
    """Sem evento capturado, `_with_tail` devolve o `detail` cru — e a classe tem de estar nele."""
    logging.disable(logging.CRITICAL)
    yield
    logging.disable(logging.NOTSET)


def test_classe_sobrevive_ao_tail_vazio(monkeypatch, tmp_path, tail_vazio):
    budget = LLMBudgetExceededError("ws-sintetico", Decimal("11.00"), Decimal("10.00"))

    result = _run_leaf(monkeypatch, tmp_path, _raising(budget))

    assert result.success is False
    assert result.detail == {FAILURE_CLASS_KEY: "budget_exhausted"}


def test_detail_leva_so_o_vocabulario_fechado(monkeypatch, tmp_path):
    """O texto da exceção vai a `error`; pela chave sai o membro do enum e nada mais."""
    result = _run_leaf(monkeypatch, tmp_path, _raising(RuntimeError("texto da exceção")))

    assert result.detail[FAILURE_CLASS_KEY] == "internal_error"
    assert result.error == "texto da exceção"


def test_sys_exit_de_script_legado_grava_unknown_explicito(monkeypatch, tmp_path):
    """Sem tipo para classificar; a presença da chave separa isto de produtor antigo."""
    result = _run_leaf(monkeypatch, tmp_path, _exiting(1))

    assert result.success is False
    assert result.detail[FAILURE_CLASS_KEY] == "unknown"


def test_sys_exit_zero_entrega_sem_classe(monkeypatch, tmp_path):
    result = _run_leaf(monkeypatch, tmp_path, _exiting(0))

    assert result.success is True
    assert FAILURE_CLASS_KEY not in (result.detail or {})
