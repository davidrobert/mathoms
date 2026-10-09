"""Releitura da cabeça UNKNOWN do trem (ADR-322 §Emenda 2026-10-09): a lista em lote
devolve UNKNOWN enquanto o GitHub não calcula a mergeabilidade, e o trem segurou ~18
de 22 runs assim com 15 PRs BEHIND atrás — 100% offline, sem rede nem relógio."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import dev.ci_advance_automerge_train as train  # noqa: E402
from dev.ci_advance_automerge_train import (  # noqa: E402
    GhCallFailed,
    advance_train,
    decide_train,
    describe_decision,
)
from dev.ci_automerge_watchdog import train_head  # noqa: E402


def _pr(number: int, status: str = "BEHIND") -> dict[str, Any]:
    return {
        "number": number,
        "title": f"PR {number}",
        "createdAt": f"2026-10-09T00:{number:02d}:00Z",
        "isDraft": False,
        "labels": [],
        "mergeStateStatus": status,
        "autoMergeRequest": {"mergeMethod": "SQUASH"},
        "headRefOid": f"{number:040d}",
    }


def _no_runs(_: dict[str, Any]) -> list[dict[str, Any]]:
    return []


@pytest.fixture(autouse=True)
def _sem_rede_nem_relogio(monkeypatch: Any) -> None:
    def _proibido(*_: Any) -> Any:
        raise AssertionError("teste chamou a API ou o relógio reais — injete state_for/pause")

    monkeypatch.setattr(train, "merge_state", _proibido)
    monkeypatch.setattr(train.time, "sleep", _proibido)


class _StateFake:
    """Responde em ordem (a última resposta se repete) e registra leituras e pausas."""

    def __init__(self, *answers: str | Exception) -> None:
        self.answers = list(answers)
        self.calls: list[int] = []
        self.pauses: list[float] = []

    def __call__(self, number: int) -> str:
        self.calls.append(number)
        answer = self.answers.pop(0) if len(self.answers) > 1 else self.answers[0]
        if isinstance(answer, Exception):
            raise answer
        return answer

    def pause(self, seconds: float) -> None:
        self.pauses.append(seconds)


def _decide(prs: list[dict[str, Any]], state: _StateFake) -> train.TrainDecision:
    return decide_train(prs, _no_runs, state, state.pause)


def test_unknown_relido_behind_e_atualizado() -> None:
    state = _StateFake("BEHIND")
    decision = _decide([_pr(1, "UNKNOWN"), _pr(2)], state)
    assert decision.pr is not None and decision.pr["number"] == 1
    assert (state.calls, state.pauses) == ([1], [])


def test_unknown_persistente_segura_sem_dizer_em_andamento() -> None:
    state = _StateFake("UNKNOWN")
    decision = _decide([_pr(1, "UNKNOWN")], state)
    assert decision.head_on_hold is not None and decision.head_state == "UNKNOWN"
    assert (state.calls, state.pauses) == ([1, 1], [train.UNKNOWN_REREAD_PAUSE_S])
    line = describe_decision(decision)
    assert "sem mergeabilidade calculada" in line and "em andamento" not in line


def test_unknown_resolvido_na_segunda_leitura() -> None:
    state = _StateFake("UNKNOWN", "BEHIND")
    decision = _decide([_pr(1, "UNKNOWN")], state)
    assert decision.pr is not None and state.calls == [1, 1]


@pytest.mark.parametrize("status", ["BEHIND", "BLOCKED", "CLEAN", "UNSTABLE"])
def test_cabeca_classificada_pela_lista_nao_e_relida(status: str) -> None:
    state = _StateFake("BEHIND")
    _decide([_pr(1, status), _pr(2)], state)
    assert state.calls == []


def test_releitura_dirty_segura_a_mesma_cabeca_do_watchdog() -> None:
    """Identidade, não igualdade: o watchdog nomeia a cabeça sem reler, e os dois não podem divergir."""
    prs = [_pr(1, "UNKNOWN"), _pr(2)]
    decision = _decide(prs, _StateFake("DIRTY"))
    assert decision.head_on_hold is train_head(prs, _no_runs)
    assert decision.head_state == "DIRTY"


def test_falha_da_api_na_releitura_segura_sem_excecao() -> None:
    decision = _decide([_pr(1, "UNKNOWN")], _StateFake(GhCallFailed(1, "HTTP 502: Bad Gateway")))
    assert decision.pr is None and decision.head_state == "UNKNOWN"


def test_conta_unknown_atras_da_cabeca() -> None:
    prs = [_pr(1, "BLOCKED"), _pr(2, "UNKNOWN"), _pr(3, "UNKNOWN"), _pr(4)]
    decision = _decide(prs, _StateFake("BEHIND"))
    assert (decision.waiting_behind, decision.waiting_unknown) == (1, 2)
    assert "1 PR(s) elegível(is) BEHIND + 2 UNKNOWN atrás" in describe_decision(decision)


def test_advance_train_rele_a_cabeca_pelo_merge_state_do_modulo(monkeypatch: Any) -> None:
    monkeypatch.setattr(train, "merge_state", _StateFake("BEHIND"))
    updated: list[int] = []
    advance_train([_pr(1, "UNKNOWN")], _no_runs, updated.append)
    assert updated == [1]
