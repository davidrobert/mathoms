"""Lógica pura do trem de auto-merge (ADR-322): seleção FIFO de 1 PR, skip de conflito/red via runs da API de Actions, predicados de órfão e stall do watchdog. Sem rede — gh nunca é chamado."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import dev.ci_advance_automerge_train as train  # noqa: E402
import dev.ci_automerge_watchdog as watchdog  # noqa: E402
from dev.ci_advance_automerge_train import (  # noqa: E402
    decide_train,
    describe_decision,
    eligible_train,
    latest_required_runs,
    out_of_train_reason,
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


def _fila_medida_2026_08_21() -> list[dict[str, Any]]:
    """Fila real do incidente: cabeça BLOCKED e 5 elegíveis BEHIND atrás dela."""
    return [
        _pr(1569, mergeStateStatus="BLOCKED", createdAt="2026-08-19T10:00:00Z"),
        _pr(1574, createdAt="2026-08-20T10:00:00Z"),
        _pr(1591, createdAt="2026-08-20T11:00:00Z"),
        _pr(1594, createdAt="2026-08-20T12:00:00Z"),
        _pr(1600, createdAt="2026-08-21T09:00:00Z"),
        _pr(1601, createdAt="2026-08-21T10:00:00Z"),
    ]


class TestDecideTrain:
    def test_hold_devolve_cabeca_e_conta_quem_espera(self) -> None:
        decision = decide_train(_fila_medida_2026_08_21(), _runs_fake({}))
        assert decision.pr is None
        assert decision.head_on_hold is not None and decision.head_on_hold["number"] == 1569
        assert decision.waiting_behind == 5

    def test_fila_vazia_nao_tem_cabeca_nem_espera(self) -> None:
        decision = decide_train([], _runs_fake({}))
        assert (decision.pr, decision.head_on_hold, decision.waiting_behind) == (None, None, 0)

    def test_pr_selecionado_nao_reporta_hold(self) -> None:
        decision = decide_train([_pr(1)], _runs_fake({}))
        assert decision.pr is not None and decision.pr["number"] == 1
        assert (decision.head_on_hold, decision.waiting_behind) == (None, 0)

    def test_conta_so_behind_atras_da_cabeca(self) -> None:
        prs = [
            _pr(1, mergeStateStatus="BLOCKED"),
            _pr(2, mergeStateStatus="DIRTY"),
            _pr(3, mergeStateStatus="BLOCKED"),
            _pr(4),
        ]
        assert decide_train(prs, _runs_fake({})).waiting_behind == 1

    def test_nao_conta_quem_esta_fora_do_trem(self) -> None:
        prs = [
            _pr(1, mergeStateStatus="BLOCKED"),
            _pr(2, isDraft=True),
            _pr(3, autoMergeRequest=None),
            _pr(4, labels=[{"name": "blocked"}]),
        ]
        assert decide_train(prs, _runs_fake({})).waiting_behind == 0

    def test_pulado_antes_da_cabeca_nao_conta_como_atras(self) -> None:
        prs = [_pr(1, mergeStateStatus="DIRTY"), _pr(2, mergeStateStatus="BLOCKED"), _pr(3)]
        decision = decide_train(prs, _runs_fake({}))
        assert decision.head_on_hold is not None and decision.head_on_hold["number"] == 2
        assert decision.waiting_behind == 1

    def test_select_pr_to_update_deriva_da_mesma_decisao(self) -> None:
        prs = _fila_medida_2026_08_21()
        assert select_pr_to_update(prs, _runs_fake({})) is decide_train(prs, _runs_fake({})).pr


def _run_main(monkeypatch: Any, capsys: Any, prs: list[dict[str, Any]], *dry: str) -> Any:
    """Executa main() sem rede; devolve (stdout, PRs que receberam update-branch)."""
    updated: list[int] = []
    monkeypatch.setattr(train, "list_open_prs", lambda: prs)
    monkeypatch.setattr(train, "runs_for_commit", lambda sha: [])
    monkeypatch.setattr(train, "update_branch", lambda number: updated.append(number))
    monkeypatch.setattr(sys, "argv", ["ci_advance_automerge_train.py", *dry])
    assert train.main() == 0
    return capsys.readouterr().out, updated


class TestMainOutput:
    """A linha final de main() é o único sinal que o operador lê no Actions —
    até 2026-08-21 ela dizia 'nenhum PR elegível BEHIND' com 5 esperando."""

    def test_hold_com_fila_atras_nomeia_cabeca_e_conta_espera(
        self, monkeypatch: Any, capsys: Any
    ) -> None:
        out, updated = _run_main(monkeypatch, capsys, _fila_medida_2026_08_21())
        assert "trem segurando" in out
        assert "#1569" in out and "5 PR(s)" in out
        assert "trem em dia" not in out
        assert updated == []

    def test_fila_vazia_diz_trem_em_dia(self, monkeypatch: Any, capsys: Any) -> None:
        out, updated = _run_main(monkeypatch, capsys, [_pr(1, autoMergeRequest=None)])
        assert "trem em dia: nenhum PR elegível BEHIND" in out
        assert "trem segurando" not in out
        assert updated == []

    def test_hold_e_fila_vazia_nao_compartilham_mensagem(
        self, monkeypatch: Any, capsys: Any
    ) -> None:
        hold, _ = _run_main(monkeypatch, capsys, _fila_medida_2026_08_21())
        vazia, _ = _run_main(monkeypatch, capsys, [])
        assert hold != vazia

    def test_hold_sem_ninguem_atras_ainda_nao_e_trem_em_dia(
        self, monkeypatch: Any, capsys: Any
    ) -> None:
        out, _ = _run_main(monkeypatch, capsys, [_pr(1, mergeStateStatus="BLOCKED")])
        assert "trem segurando" in out and "nenhum PR elegível atrás" in out
        assert "trem em dia" not in out

    def test_pr_elegivel_e_atualizado(self, monkeypatch: Any, capsys: Any) -> None:
        out, updated = _run_main(monkeypatch, capsys, [_pr(7)])
        assert "update-branch #7" in out
        assert updated == [7]

    def test_dry_run_decide_sem_atualizar(self, monkeypatch: Any, capsys: Any) -> None:
        out, updated = _run_main(monkeypatch, capsys, [_pr(7)], "--dry-run")
        assert "update-branch #7" in out
        assert updated == []


class TestDescribeDecision:
    def test_hold_declara_o_merge_state_da_cabeca(self) -> None:
        decision = decide_train(_fila_medida_2026_08_21(), _runs_fake({}))
        assert "mergeStateStatus=BLOCKED" in describe_decision(decision)

    def test_unknown_tambem_segura_e_aparece_na_mensagem(self) -> None:
        prs = [_pr(1, mergeStateStatus="UNKNOWN"), _pr(2)]
        assert "mergeStateStatus=UNKNOWN" in describe_decision(decide_train(prs, _runs_fake({})))


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


class TestOutOfTrainReason:
    def test_pr_limpo_concorre_a_cabeca(self) -> None:
        assert out_of_train_reason(_pr(1), _runs_fake({})) is None

    def test_dirty_declara_conflito(self) -> None:
        reason = out_of_train_reason(_pr(1, mergeStateStatus="DIRTY"), _runs_fake({}))
        assert reason is not None and "conflito de merge" in reason

    def test_required_em_failure_declara_red(self) -> None:
        reason = out_of_train_reason(_pr(1), _runs_fake({1: [RUN_CI_FAIL]}))
        assert reason is not None and "workflow required" in reason

    def test_dirty_nao_gasta_chamada_de_runs(self) -> None:
        """Fetcher é lazy de propósito: o trem roda 2×/h, o watchdog outras 2×/h e a
        fila real tem tido DIRTY na cabeça — buscar runs de quem já saiu é chamada
        de API jogada fora numa API onde rate-limit secundário já foi suspeitado."""

        def _explode(pr: dict[str, Any]) -> list[dict[str, Any]]:
            raise AssertionError(f"runs buscados para PR DIRTY #{pr['number']}")

        assert out_of_train_reason(_pr(1, mergeStateStatus="DIRTY"), _explode) is not None

    def test_skip_impresso_repete_o_motivo_do_predicado(self, capsys: Any) -> None:
        """A tabela de sintomas do runbook cita `skip #N: conflito de merge` — a linha
        sai do predicado, não de uma segunda cópia da frase que envelhece sozinha."""
        prs = [_pr(1, mergeStateStatus="DIRTY"), _pr(2)]
        decide_train(prs, _runs_fake({}))
        reason = out_of_train_reason(prs[0], _runs_fake({}))
        assert f"skip #1: {reason}" in capsys.readouterr().out


class TestCabecaUnica:
    """decide_train e o train_head do watchdog derivam a cabeça em separado. O
    desfecho difere de propósito (um para nela, o outro a devolve mesmo sem BEHIND);
    QUEM ela é não pode divergir, senão a issue de stall nomeia um PR e o hold do
    trem reporta outro. Concordavam por coincidência — as duas repetiam o mesmo par
    de condições — até out_of_train_reason virar fonte única."""

    @pytest.mark.parametrize("status", ["BLOCKED", "CLEAN", "UNKNOWN", "UNSTABLE", "HAS_HOOKS"])
    def test_cabeca_nao_behind_e_a_mesma_nos_dois(self, status: str) -> None:
        prs = [_pr(1, mergeStateStatus=status), _pr(2), _pr(3)]
        runs = _runs_fake({})
        head = train_head(prs, runs)
        assert head is not None and head["number"] == 1
        assert decide_train(prs, runs).head_on_hold is head

    def test_concordam_sobre_a_cabeca_depois_de_pular_excluidos(self) -> None:
        prs = [
            _pr(1, mergeStateStatus="DIRTY"),
            _pr(2),
            _pr(3, mergeStateStatus="BLOCKED"),
        ]
        runs = _runs_fake({2: [RUN_CI_FAIL]})
        head = train_head(prs, runs)
        assert head is not None and head["number"] == 3
        assert decide_train(prs, runs).head_on_hold is head

    def test_fila_medida_no_incidente(self) -> None:
        prs = _fila_medida_2026_08_21()
        runs = _runs_fake({})
        assert decide_train(prs, runs).head_on_hold is train_head(prs, runs)

    def test_cabeca_behind_sai_em_campo_diferente_e_ainda_e_a_mesma(self) -> None:
        """As semânticas seguem distintas: com a cabeça BEHIND o trem a devolve para
        atualizar (`pr`, e `head_on_hold` fica None) e o watchdog a devolve como
        cabeça. Campos diferentes, mesmo PR."""
        prs = [_pr(1), _pr(2)]
        runs = _runs_fake({})
        decision = decide_train(prs, runs)
        assert decision.head_on_hold is None
        assert decision.pr is train_head(prs, runs)

    def test_fila_sem_ninguem_dentro_nao_tem_cabeca_nos_dois(self) -> None:
        prs = [_pr(1, mergeStateStatus="DIRTY"), _pr(2, mergeStateStatus="DIRTY")]
        runs = _runs_fake({})
        assert decide_train(prs, runs).head_on_hold is None
        assert train_head(prs, runs) is None

    def test_motivo_novo_no_predicado_move_as_duas_cabecas(self, monkeypatch: Any) -> None:
        """O terceiro motivo já previsto (403 terminal do PR que toca
        `.github/workflows/**`, ADR-322 §Emenda 2026-08-08) entra em
        out_of_train_reason e só ali. Quem reinlinar as condições para de enxergá-lo
        e volta a nomear outra cabeça."""

        def _com_403_terminal(pr: dict[str, Any], runs_for: Any) -> str | None:
            if pr["number"] == 1:
                return "403 terminal: update-branch não move este PR"
            return None

        monkeypatch.setattr(train, "out_of_train_reason", _com_403_terminal)
        monkeypatch.setattr(watchdog, "out_of_train_reason", _com_403_terminal)
        prs = [_pr(1, mergeStateStatus="BLOCKED"), _pr(2, mergeStateStatus="BLOCKED"), _pr(3)]
        runs = _runs_fake({})
        head = train_head(prs, runs)
        assert head is not None and head["number"] == 2
        assert decide_train(prs, runs).head_on_hold is head
