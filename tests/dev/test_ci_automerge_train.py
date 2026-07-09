"""Lógica pura do trem de auto-merge (ADR-322): seleção FIFO de 1 PR, skip de conflito/red, predicados de órfão e stall do watchdog. Sem rede — gh nunca é chamado."""

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
    required_check_failed,
    select_pr_to_update,
)
from dev.ci_automerge_watchdog import (  # noqa: E402
    aggregator_green,
    is_orphan_run_set,
    is_stalled,
    stalled_without_runs,
    train_head,
)

NOW = datetime(2026, 7, 9, 12, 0, tzinfo=timezone.utc)


def _pr(number: int, **overrides: Any) -> dict[str, Any]:
    pr: dict[str, Any] = {
        "number": number,
        "title": f"PR {number}",
        "createdAt": f"2026-07-09T00:{number:02d}:00Z",
        "isDraft": False,
        "labels": [],
        "mergeStateStatus": "BEHIND",
        "autoMergeRequest": {"mergeMethod": "SQUASH"},
        "statusCheckRollup": [],
        "headRefOid": f"{number:040d}",
        "headRefName": f"agent/x/{number}",
    }
    pr.update(overrides)
    return pr


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
        selected = select_pr_to_update([_pr(2), _pr(1)])
        assert selected is not None and selected["number"] == 1

    def test_cabeca_pendente_segura_o_trem(self) -> None:
        assert select_pr_to_update([_pr(1, mergeStateStatus="BLOCKED"), _pr(2)]) is None

    def test_dirty_sai_do_trem_e_proximo_assume(self) -> None:
        selected = select_pr_to_update([_pr(1, mergeStateStatus="DIRTY"), _pr(2)])
        assert selected is not None and selected["number"] == 2

    def test_required_check_failure_sai_do_trem(self) -> None:
        red = _pr(1, statusCheckRollup=[{"name": "All checks green", "conclusion": "FAILURE"}])
        selected = select_pr_to_update([red, _pr(2)])
        assert selected is not None and selected["number"] == 2

    def test_check_informativo_failure_nao_tira_do_trem(self) -> None:
        pr = _pr(1, statusCheckRollup=[{"name": "Lighthouse", "conclusion": "FAILURE"}])
        selected = select_pr_to_update([pr])
        assert selected is not None and selected["number"] == 1

    def test_fila_vazia_retorna_none(self) -> None:
        assert select_pr_to_update([]) is None


class TestRequiredCheckFailed:
    def test_detecta_failure_em_required_context(self) -> None:
        pr = _pr(
            1, statusCheckRollup=[{"name": "Title (Conventional Commits)", "conclusion": "FAILURE"}]
        )
        assert required_check_failed(pr)

    def test_ignora_success_e_pending(self) -> None:
        pr = _pr(1, statusCheckRollup=[{"name": "All checks green", "conclusion": "SUCCESS"}])
        assert not required_check_failed(pr)

    def test_agregador_stale_com_sibling_cancelled_nao_e_red(self) -> None:
        pr = _pr(
            1,
            statusCheckRollup=[
                {"name": "All checks green", "conclusion": "FAILURE"},
                {"name": "Backend tests (backend/tests/)", "conclusion": "CANCELLED"},
            ],
        )
        assert not required_check_failed(pr)

    def test_agregador_failure_sem_cancelled_e_red_genuino(self) -> None:
        pr = _pr(
            1,
            statusCheckRollup=[
                {"name": "All checks green", "conclusion": "FAILURE"},
                {"name": "Backend tests (backend/tests/)", "conclusion": "FAILURE"},
            ],
        )
        assert required_check_failed(pr)

    def test_title_failure_e_red_mesmo_com_cancelled(self) -> None:
        pr = _pr(
            1,
            statusCheckRollup=[
                {"name": "Title (Conventional Commits)", "conclusion": "FAILURE"},
                {"name": "Backend tests (backend/tests/)", "conclusion": "CANCELLED"},
            ],
        )
        assert required_check_failed(pr)


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

    def test_aggregator_green(self) -> None:
        pr = _pr(1, statusCheckRollup=[{"name": "All checks green", "conclusion": "SUCCESS"}])
        assert aggregator_green(pr)
        assert not aggregator_green(_pr(2))

    def test_train_head_pula_dirty_e_red(self) -> None:
        prs = [
            _pr(1, mergeStateStatus="DIRTY"),
            _pr(2, statusCheckRollup=[{"name": "All checks green", "conclusion": "FAILURE"}]),
            _pr(3, mergeStateStatus="BLOCKED"),
        ]
        head = train_head(prs)
        assert head is not None and head["number"] == 3
