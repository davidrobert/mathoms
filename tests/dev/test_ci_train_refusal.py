"""Recusa da API no update-branch: 403 é terminal para o PR, nunca para o run
(ADR-322 §Emenda 2026-08-25). Arquivo próprio — o de seleção do trem já estava em
584 linhas e P2 veda >500. Sem rede: `gh` nunca é chamado."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import dev.ci_advance_automerge_train as train  # noqa: E402
from dev.ci_advance_automerge_train import describe_decision  # noqa: E402
from tests.dev.test_ci_automerge_train import _pr, _runs_fake  # noqa: E402


def _refusal(status: int = 403) -> Any:
    """Recusa da API na forma que `gh` entrega: status no stderr, rc != 0."""
    stderr = (
        f"gh: Resource not accessible by personal access token (HTTP {status})\n"
        if status != 500
        else f"gh: Internal Server Error (HTTP {status})\n"
    )
    return train.GhCallFailed(1, stderr)


def _updater_that_refuses(refuse: set[int], log: list[int], status: int = 403):
    def updater(number: int) -> None:
        log.append(number)
        if number in refuse:
            raise _refusal(status)

    return updater


class TestGhCallFailed:
    """A classificação existe porque o desfecho depende dela: 4xx é veredito da
    API, 5xx é indisponibilidade. Sem status, `_gh` não sabe qual re-tentar."""

    def test_status_sai_do_stderr(self) -> None:
        assert _refusal(403).status == 403

    @pytest.mark.parametrize("status", [400, 403, 404, 422])
    def test_4xx_e_veredito(self, status: int) -> None:
        assert _refusal(status).is_verdict

    @pytest.mark.parametrize("status", [500, 502, 503])
    def test_5xx_nao_e_veredito(self, status: int) -> None:
        assert not train.GhCallFailed(1, f"gh: erro (HTTP {status})").is_verdict

    def test_sem_status_no_stderr_nao_e_veredito(self) -> None:
        """Falha sem HTTP legível (rede, binário ausente) mantém o retry — a
        alternativa seria tratar o desconhecido como recusa definitiva."""
        assert not train.GhCallFailed(127, "gh: command not found").is_verdict

    def test_describe_cita_status_e_causa(self) -> None:
        assert "HTTP 403" in _refusal().describe()
        assert "personal access token" in _refusal().describe()


class TestGhRetryPorClasse:
    """Em 2026-08-17 o retry cego re-tentou 9× um 403 de escopo de PAT e
    recuperou 0 de 10 (ADR-210 §Adendo 2026-08-21c). O gasto é relógio dentro
    de um run que segura a fila."""

    def _gh_com_falhas(self, monkeypatch: Any, stderr: str) -> list[list[str]]:
        chamadas: list[list[str]] = []

        def fake_run(cmd: list[str], **kwargs: Any) -> Any:
            chamadas.append(cmd)
            return subprocess.CompletedProcess(cmd, 1, "", stderr)

        monkeypatch.setattr(train.subprocess, "run", fake_run)
        monkeypatch.setattr(train.time, "sleep", lambda _s: None)
        return chamadas

    def test_403_sai_na_primeira_tentativa(self, monkeypatch: Any) -> None:
        chamadas = self._gh_com_falhas(monkeypatch, "gh: negado (HTTP 403)")
        with pytest.raises(train.GhCallFailed) as exc:
            train._gh("api", "-X", "PUT", "repos/o/r/pulls/1/update-branch")
        assert len(chamadas) == 1
        assert exc.value.status == 403

    def test_503_ainda_re_tenta_uma_vez(self, monkeypatch: Any) -> None:
        chamadas = self._gh_com_falhas(monkeypatch, "gh: indisponível (HTTP 503)")
        with pytest.raises(train.GhCallFailed):
            train._gh("pr", "list")
        assert len(chamadas) == 2


class TestRecusaNaoMataORun:
    """ADR-322 §Emenda 2026-08-08: o 403 é terminal para AQUELE PR, nunca para o
    run. Antes deste fix a exceção subia até main(), o processo saía 1 e nenhum
    outro PR da fila era atualizado — a fila inteira parava por causa da cabeça."""

    def test_recusa_na_cabeca_deixa_o_proximo_ser_atualizado(self, capsys: Any) -> None:
        tentados: list[int] = []
        decision = train.advance_train(
            [_pr(1), _pr(2)], _runs_fake({}), _updater_that_refuses({1}, tentados)
        )
        assert tentados == [1, 2]
        assert decision.pr is not None and decision.pr["number"] == 2
        assert [r.number for r in decision.refused] == [1]
        assert "skip #1" in capsys.readouterr().out

    def test_fila_inteira_recusando_para_no_teto_sem_dizer_trem_em_dia(self) -> None:
        tentados: list[int] = []
        prs = [_pr(n) for n in (1, 2, 3, 4, 5)]
        decision = train.advance_train(
            prs, _runs_fake({}), _updater_that_refuses({1, 2, 3, 4, 5}, tentados)
        )
        assert len(tentados) == train.MAX_REFUSALS_PER_RUN
        assert decision.pr is None and [r.number for r in decision.refused] == [1, 2, 3]
        assert "trem em dia" not in describe_decision(decision)

    def test_5xx_no_update_sobe_e_nao_vira_skip(self) -> None:
        """Indisponibilidade não é veredito sobre o PR: engolir viraria skip de
        um PR são, e ele sairia do trem sem motivo."""
        tentados: list[int] = []
        with pytest.raises(train.GhCallFailed):
            train.advance_train(
                [_pr(1), _pr(2)], _runs_fake({}), _updater_that_refuses({1}, tentados, status=503)
            )
        assert tentados == [1]

    def test_recusa_nao_conta_como_update_o_teto_de_1_por_run_vale(self) -> None:
        """§D1: 1 update-branch bem-sucedido por run. Tentativa recusada não
        atualizou nada, então prosseguir não afrouxa o invariante."""
        atualizados: list[int] = []

        def updater(number: int) -> None:
            if number == 1:
                raise _refusal()
            atualizados.append(number)

        train.advance_train([_pr(1), _pr(2), _pr(3)], _runs_fake({}), updater)
        assert atualizados == [2]

    def test_cabeca_pendente_ainda_segura_mesmo_apos_recusa(self) -> None:
        """A recusa pula o PR recusado; ela não converte hold em pulo — quem
        segura o trem continua segurando (ADR-322 §D1)."""
        prs = [_pr(1), _pr(2, mergeStateStatus="BLOCKED"), _pr(3)]
        decision = train.advance_train(prs, _runs_fake({}), _updater_that_refuses({1}, []))
        assert decision.pr is None
        assert decision.head_on_hold is not None and decision.head_on_hold["number"] == 2
        assert [r.number for r in decision.refused] == [1]

    def test_linha_final_nomeia_os_recusados_e_a_causa(self) -> None:
        decision = train.advance_train(
            [_pr(1), _pr(2)], _runs_fake({}), _updater_that_refuses({1}, [])
        )
        linha = describe_decision(decision)
        assert "#1" in linha and "workflow" in linha and "update-branch #2" in linha


class TestCausaSaiDoStatusObservado:
    """A linha final acusava "403 é PAT sem escopo workflow" para QUALQUER 4xx —
    404, 422 e 429 recebiam o mesmo diagnóstico inventado."""

    @pytest.mark.parametrize("status", [404, 422])
    def test_4xx_que_nao_e_403_nao_recebe_o_diagnostico_do_403(self, status: int) -> None:
        decision = train.advance_train(
            [_pr(1), _pr(2)], _runs_fake({}), _updater_that_refuses({1}, [], status=status)
        )
        linha = describe_decision(decision)
        assert "PAT sem escopo" not in linha
        assert str(status) in linha

    def test_403_ainda_explica_o_caso_provavel_sem_fechar_a_questao(self) -> None:
        decision = train.advance_train([_pr(1)], _runs_fake({}), _updater_that_refuses({1}, []))
        linha = describe_decision(decision)
        assert "workflow" in linha and "costuma ser" in linha

    def test_refusal_carrega_status_e_causa(self) -> None:
        decision = train.advance_train([_pr(1)], _runs_fake({}), _updater_that_refuses({1}, []))
        assert decision.refused[0].status == 403
        assert "403" in decision.refused[0].detail


class TestRateLimitNaoEVeredito:
    """429 e o 403 de rate limit secundário são 4xx pelo número e transientes
    pelo mecanismo — a medição de 0/10 recuperados é sobre 403 de ESCOPO."""

    def test_429_sobe_em_vez_de_virar_skip(self) -> None:
        tentados: list[int] = []
        with pytest.raises(train.GhCallFailed):
            train.advance_train(
                [_pr(1), _pr(2)], _runs_fake({}), _updater_that_refuses({1}, tentados, status=429)
            )
        assert tentados == [1]

    def test_403_de_rate_limit_secundario_nao_e_veredito(self) -> None:
        falha = train.GhCallFailed(1, "gh: You have exceeded a secondary rate limit (HTTP 403)")
        assert falha.is_rate_limited and not falha.is_verdict

    def test_403_de_escopo_continua_veredito(self) -> None:
        assert _refusal(403).is_verdict and not _refusal(403).is_rate_limited


class TestTetoNaoSeDisfarcaDeFilaVazia:
    def test_teto_declara_que_a_fila_nao_foi_esgotada(self) -> None:
        """`nada mais a atualizar` com 2 PRs nunca tentados é a mesma classe do
        'trem em dia' de 08-21: enfileiramento vivo lido como fila vazia."""
        prs = [_pr(n) for n in (1, 2, 3, 4, 5)]
        decision = train.advance_train(
            prs, _runs_fake({}), _updater_that_refuses({1, 2, 3, 4, 5}, [])
        )
        linha = describe_decision(decision)
        assert decision.hit_refusal_cap
        assert "NÃO foi" in linha and "teto" in linha
        assert "nada mais a atualizar" not in linha

    def test_fila_realmente_esgotada_nao_fala_em_teto(self) -> None:
        decision = train.advance_train([_pr(1)], _runs_fake({}), _updater_that_refuses({1}, []))
        linha = describe_decision(decision)
        assert not decision.hit_refusal_cap and "teto" not in linha
