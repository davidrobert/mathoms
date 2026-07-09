"""Lógica pura do trem de auto-merge (ADR-322): seleção FIFO de 1 PR, skip de conflito/red via runs da API de Actions, predicados de órfão e stall do watchdog. Sem rede — gh nunca é chamado."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dev.ci_advance_automerge_train import (  # noqa: E402
    eligible_train,
    latest_required_runs,
    required_workflow_failed,
    required_workflows_green,
    select_pr_to_update,
)
from dev.ci_automerge_watchdog import (  # noqa: E402
    is_orphan_run_set,
    is_stalled,
    stalled_without_runs,
    train_head,
)

NOW = datetime(2026, 7, 9, 12, 0, tzinfo=timezone.utc)

RUN_CI_OK = {
    "name": "CI",
    "status": "completed",
    "conclusion": "success",
    "updatedAt": "2026-07-09T11:30:00Z",
}
RUN_CI_FAIL = {
    "name": "CI",
    "status": "completed",
    "conclusion": "failure",
    "updatedAt": "2026-07-09T11:30:00Z",
}
RUN_CI_CANCEL = {
    "name": "CI",
    "status": "completed",
    "conclusion": "cancelled",
    "updatedAt": "2026-07-09T11:30:00Z",
}
RUN_CI_LIVE = {
    "name": "CI",
    "status": "in_progress",
    "conclusion": "",
    "updatedAt": "2026-07-09T11:30:00Z",
}
RUN_PRQ_OK = {
    "name": "PR Quality",
    "status": "completed",
    "conclusion": "success",
    "updatedAt": "2026-07-09T11:30:00Z",
}
RUN_PRQ_FAIL = {
    "name": "PR Quality",
    "status": "completed",
    "conclusion": "failure",
    "updatedAt": "2026-07-09T11:30:00Z",
}
RUN_SECURITY_FAIL = {
    "name": "Security",
    "status": "completed",
    "conclusion": "failure",
    "updatedAt": "2026-07-09T11:30:00Z",
}


def _pr(number: int, **overrides: Any) -> dict[str, Any]:
    pr: dict[str, Any] = {
        "number": number,
        "title": f"PR {number}",
        "createdAt": f"2026-07-09T00:{number:02d}:00Z",
        "isDraft": False,
        "labels": [],
        "mergeStateStatus": "BEHIND",
        "autoMergeRequest": {"mergeMethod": "SQUASH"},
        "headRefOid": f"{number:040d}",
        "headRefName": f"agent/x/{number}",
    }
    pr.update(overrides)
    return pr


def _runs_fake(runs_by_number: dict[int, list[dict[str, Any]]]):
    return lambda pr: runs_by_number.get(pr["number"], [])


class TestEligibleTrain:
    def test_filtra_sem_automerge_draft_e_label_excluida(self) -> None:
        prs = [
            _pr(1, autoMergeRequest=None),
            _pr(2, isDraft=True),
            _pr(3, labels=[{"name": "do-not-merge"}]),
            _pr(4),
        ]
        assert [pr["number"] for pr in eligible_train(prs)] == [4]

    def test_ordena_fifo_por_created_at(self) -> None:
        prs = [_pr(9), _pr(2), _pr(5)]
        assert [pr["number"] for pr in eligible_train(prs)] == [2, 5, 9]


class TestSelectPrToUpdate:
    def test_cabeca_behind_e_selecionada(self) -> None:
        selected = select_pr_to_update([_pr(2), _pr(1)], _runs_fake({}))
        assert selected is not None and selected["number"] == 1

    def test_cabeca_pendente_segura_o_trem(self) -> None:
        prs = [_pr(1, mergeStateStatus="BLOCKED"), _pr(2)]
        assert select_pr_to_update(prs, _runs_fake({})) is None

    def test_dirty_sai_do_trem_e_proximo_assume(self) -> None:
        prs = [_pr(1, mergeStateStatus="DIRTY"), _pr(2)]
        selected = select_pr_to_update(prs, _runs_fake({}))
        assert selected is not None and selected["number"] == 2

    def test_workflow_required_failure_sai_do_trem(self) -> None:
        selected = select_pr_to_update([_pr(1), _pr(2)], _runs_fake({1: [RUN_CI_FAIL]}))
        assert selected is not None and selected["number"] == 2

    def test_workflow_nao_required_failure_nao_tira_do_trem(self) -> None:
        selected = select_pr_to_update([_pr(1)], _runs_fake({1: [RUN_SECURITY_FAIL]}))
        assert selected is not None and selected["number"] == 1

    def test_fila_vazia_retorna_none(self) -> None:
        assert select_pr_to_update([], _runs_fake({})) is None


class TestRequiredWorkflowPredicates:
    def test_failure_genuino_e_red(self) -> None:
        assert required_workflow_failed([RUN_CI_FAIL, RUN_PRQ_OK])

    def test_cancelled_e_supersede_nao_red(self) -> None:
        assert not required_workflow_failed([RUN_CI_CANCEL, RUN_PRQ_OK])

    def test_run_mais_novo_ganha_do_mais_velho(self) -> None:
        assert not required_workflow_failed([RUN_CI_OK, RUN_CI_FAIL])
        assert required_workflow_failed([RUN_CI_FAIL, RUN_CI_OK])

    def test_latest_required_runs_ignora_nao_required(self) -> None:
        assert latest_required_runs([RUN_SECURITY_FAIL]) == {}

    def test_green_exige_todos_required_sucesso(self) -> None:
        assert required_workflows_green([RUN_CI_OK, RUN_PRQ_OK])
        assert not required_workflows_green([RUN_CI_OK])
        assert not required_workflows_green([RUN_CI_OK, RUN_PRQ_FAIL])
        assert not required_workflows_green([RUN_CI_LIVE, RUN_PRQ_OK])
        assert not required_workflows_green([])


class TestWatchdogPredicates:
    def test_orfao_todos_action_required(self) -> None:
        runs = [
            {
                "conclusion": "action_required",
                "status": "completed",
                "updatedAt": "2026-07-09T11:00:00Z",
            }
        ]
        assert is_orphan_run_set(runs)

    def test_nao_orfao_com_run_real(self) -> None:
        runs = [
            {
                "conclusion": "action_required",
                "status": "completed",
                "updatedAt": "2026-07-09T11:00:00Z",
            },
            {"conclusion": "", "status": "in_progress", "updatedAt": "2026-07-09T11:05:00Z"},
        ]
        assert not is_orphan_run_set(runs)

    def test_sem_runs_nao_e_orfao(self) -> None:
        assert not is_orphan_run_set([])

    def test_sem_runs_nao_decide_stall(self) -> None:
        assert not is_stalled([], NOW)

    def test_sem_runs_com_pr_fresco_fica_na_carencia(self) -> None:
        pr = _pr(1, updatedAt="2026-07-09T11:58:00Z")
        assert not stalled_without_runs(pr, NOW)

    def test_sem_runs_com_pr_parado_ha_mais_de_60min_e_stall(self) -> None:
        pr = _pr(1, updatedAt="2026-07-09T10:30:00Z")
        assert stalled_without_runs(pr, NOW)

    def test_stall_runs_completados_ha_mais_de_60min(self) -> None:
        runs = [
            {"status": "completed", "conclusion": "failure", "updatedAt": "2026-07-09T10:30:00Z"}
        ]
        assert is_stalled(runs, NOW)

    def test_sem_stall_com_run_ativo(self) -> None:
        runs = [{"status": "in_progress", "conclusion": "", "updatedAt": "2026-07-09T10:00:00Z"}]
        assert not is_stalled(runs, NOW)

    def test_sem_stall_com_run_recente(self) -> None:
        runs = [
            {"status": "completed", "conclusion": "success", "updatedAt": "2026-07-09T11:30:00Z"}
        ]
        assert not is_stalled(runs, NOW)

    def test_train_head_pula_dirty_e_red(self) -> None:
        prs = [
            _pr(1, mergeStateStatus="DIRTY"),
            _pr(2),
            _pr(3, mergeStateStatus="BLOCKED"),
        ]
        head = train_head(prs, _runs_fake({2: [RUN_CI_FAIL]}))
        assert head is not None and head["number"] == 3
