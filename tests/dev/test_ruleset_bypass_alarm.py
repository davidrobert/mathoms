"""Alarme do Ruleset de main (ADR-448): `bypass_actors` fica `[]` fora de
uma janela de break-glass, e o gate não enfraquece. Sem rede — `gh` nunca é
chamado. History e GET reproduzem o medido em 2026-10-09."""

from __future__ import annotations

import sys
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import dev.ci_audit_merge_protection as audit  # noqa: E402
import dev.ruleset_bypass_alarm as alarm  # noqa: E402
from tests.dev._merge_audit_fake_gh import (  # noqa: E402
    NOW,
    FakeGh,
    at,
    incident,
    iso,
    ruleset,
    ruleset_state,
)

APLICACAO = (52592012, at(seconds=0.617), ruleset_state())
ANTES_DA_448 = (47636571, "2026-08-25T19:40:01Z", ruleset_state(bypass=1))


def _history(*versions: tuple[int, str, dict]) -> list[tuple[int, str, dict]]:
    """Mais nova primeiro, como a API devolve, com a aplicação e o regime anterior."""
    return [*versions, APLICACAO, ANTES_DA_448]


def _sweep(run: FakeGh) -> int:
    return audit.main(["--sweep"], run, NOW)


def _creates(run: FakeGh) -> list[str]:
    return [c for c in run.writes if c.startswith("issue create")]


class TestSweepNaoLeAusenciaComoZero:
    """`--jq '.bypass_actors|length'` com token sem admin dá `0`: a API omite a
    chave. É o alarme mudo exatamente quando não há quem o leia."""

    @pytest.mark.parametrize(
        "resposta", [ruleset(admin=False), {**ruleset(), "bypass_actors": None}]
    )
    def test_chave_ausente_ou_nula_e_nao_medido(self, resposta: dict, capsys: Any) -> None:
        run = FakeGh(ruleset=resposta)
        assert _sweep(run) == 2
        out = capsys.readouterr()
        assert "NÃO MEDIDO" in out.err and "bypass_actors" in out.err
        assert run.writes == [] and not any("rule-suites" in c for c in run.calls)

    def test_erro_de_api_que_nao_e_404_e_nao_medido(self) -> None:
        run = FakeGh(ruleset_error="gh api: Bad Gateway (HTTP 502)")
        assert _sweep(run) == 2 and run.writes == []


class TestJanelasDoHistory:
    """O sweep diário quase nunca pega uma concessão aberta (o ensaio durou
    703 ms): ele varre as janelas desde a aplicação da ADR-448."""

    def test_ensaio_de_703ms_fica_em_silencio(self, capsys: Any) -> None:
        history = _history(
            (52592029, at(seconds=11.402), ruleset_state()),
            (52592028, at(seconds=10.699), ruleset_state(bypass=1)),
        )
        run = FakeGh(history=history)
        assert _sweep(run) == 0
        assert run.writes == [] and "dentro da tolerância" in capsys.readouterr().out

    def test_janela_fechada_de_20min_alarma(self) -> None:
        history = _history(
            (3, at(minutes=30), ruleset_state()), (2, at(minutes=10), ruleset_state(bypass=1))
        )
        run = FakeGh(history=history)
        _sweep(run)
        assert len(_creates(run)) == 1
        assert "<!-- merge-audit:ruleset-window=2 -->" in _creates(run)[0]

    def test_janela_aberta_alem_da_tolerancia_alarma(self) -> None:
        aberta = (2, iso(NOW - timedelta(minutes=20)), ruleset_state(bypass=1))
        run = FakeGh(ruleset=ruleset(bypass=1), history=_history(aberta))
        _sweep(run)
        assert "ainda aberta" in _creates(run)[0]

    def test_janela_aberta_dentro_da_tolerancia_nao_alarma(self) -> None:
        aberta = (2, iso(NOW - timedelta(minutes=5)), ruleset_state(bypass=1))
        run = FakeGh(ruleset=ruleset(bypass=1), history=_history(aberta))
        _sweep(run)
        assert run.writes == []

    def test_tolerancia_e_de_15_minutos(self) -> None:
        assert alarm.BREAK_GLASS_TOLERANCE == timedelta(minutes=15)

    def test_enforcement_desligado_alarma_sem_tolerancia(self) -> None:
        """ADR-448 D3: o toggle não é break-glass — 1 s já é incidente."""
        history = _history(
            (3, at(minutes=10, seconds=1), ruleset_state()),
            (2, at(minutes=10), ruleset_state(enforcement="disabled")),
        )
        run = FakeGh(history=history)
        _sweep(run)
        assert "`enforcement` = `disabled`" in _creates(run)[0]

    def test_gate_sem_o_required_check_alarma_sem_tolerancia(self) -> None:
        history = _history(
            (3, at(minutes=10, seconds=1), ruleset_state()),
            (2, at(minutes=10), ruleset_state(gate=False)),
        )
        run = FakeGh(history=history)
        _sweep(run)
        assert "fora dos required checks" in _creates(run)[0]

    def test_regime_anterior_a_adr448_nao_e_janela(self) -> None:
        """05-03→10-09 o bypass do Admin ERA a regra (ADR-415 D2): 5 meses de
        `bypass_actors` não-vazio não podem virar alarme — nem custar leitura."""
        run = FakeGh(history=_history())
        _sweep(run)
        assert run.writes == []
        assert not any(c.endswith(f"/history/{ANTES_DA_448[0]}") for c in run.calls)

    def test_historico_truncado_vira_nao_medido(self) -> None:
        cheio = [(i, at(minutes=i), ruleset_state()) for i in range(1000, 0, -1)]
        assert _sweep(FakeGh(history=cheio)) == 2


class TestAlarmeComoEstadoVivo:
    """Janela fechada é passado: fechada, registrada. Janela aberta é estado:
    fechar a issue com a condição de pé não pode silenciar o alarme."""

    def _aberta(self, **tables: Any) -> FakeGh:
        aberta = (2, iso(NOW - timedelta(minutes=20)), ruleset_state(bypass=1))
        return FakeGh(ruleset=ruleset(bypass=1), history=_history(aberta), **tables)

    def test_janela_aberta_com_issue_fechada_e_reaberta(self) -> None:
        run = self._aberta(issues=[incident("ruleset-window=2", number=55, state="closed")])
        _sweep(run)
        assert run.writes == [
            "issue reopen 55 --comment Reaberta pelo detector: a condição continua de pé (ADR-448)."
        ]

    def test_janela_aberta_com_issue_aberta_nao_comenta(self) -> None:
        run = self._aberta(issues=[incident("ruleset-window=2", number=55)])
        _sweep(run)
        assert run.writes == []

    def test_janela_fechada_registrada_nao_reabre(self) -> None:
        history = _history(
            (3, at(minutes=30), ruleset_state()), (2, at(minutes=10), ruleset_state(bypass=1))
        )
        run = FakeGh(history=history, issues=[incident("ruleset-window=2", state="closed")])
        _sweep(run)
        assert run.writes == []


class TestRulesetAusente:
    """404 é `main` sem proteção: alarme máximo, nunca 'não medido'."""

    @pytest.mark.parametrize("modo", [["--sweep"], ["--ruleset"]])
    def test_404_abre_alarme(self, modo: list[str]) -> None:
        run = FakeGh(ruleset_error="gh api: Not Found (HTTP 404)")
        audit.main(modo, run, NOW)
        assert f"<!-- merge-audit:{alarm.MISSING_KEY} -->" in _creates(run)[0]

    def test_404_com_alarme_fechado_reabre(self) -> None:
        run = FakeGh(
            ruleset_error="gh api: Not Found (HTTP 404)",
            issues=[incident(alarm.MISSING_KEY, number=8, state="closed")],
        )
        audit.main(["--ruleset"], run, NOW)
        assert run.writes[0].startswith("issue reopen 8")


class TestTripwireSemAdmin:
    """O sweep precisa de admin e hoje é rodado à mão. O push roda com o
    `GITHUB_TOKEN`, que lê enforcement, rules e `updated_at` — o bastante para
    ver concessão e toggle no merge seguinte."""

    def _tripwire(self, **tables: Any) -> tuple[int, FakeGh]:
        tables.setdefault("ruleset", ruleset(admin=False))
        run = FakeGh(**tables)
        return audit.main(["--ruleset"], run), run

    def test_mudanca_nova_abre_issue_de_evento(self) -> None:
        rc, run = self._tripwire()
        assert rc == 0
        assert "ruleset-updated=2026-10-09T15:53:52.112+00:00" in _creates(run)[0]

    def test_nao_precisa_de_bypass_actors_nem_de_endpoint_de_admin(self) -> None:
        _, run = self._tripwire()
        leituras = [c for c in run.calls if c.startswith("api ")]
        assert not any("/history" in c or "rule-suites" in c for c in leituras)

    def test_mesma_mudanca_fechada_nao_volta(self) -> None:
        chave = "ruleset-updated=2026-10-09T15:53:52.112+00:00"
        _, run = self._tripwire(issues=[incident(chave, state="closed")])
        assert run.writes == []

    def test_Z_e_offset_dao_a_mesma_chave(self) -> None:
        """O GET sem admin devolve `Z`; com admin, `-04:00`. A chave é o instante."""
        _, run = self._tripwire(ruleset=ruleset(updated_at="2026-10-09T11:53:52.112-04:00"))
        chave = "ruleset-updated=2026-10-09T15:53:52.112+00:00"
        assert chave in _creates(run)[0]

    @pytest.mark.parametrize(
        ("estado", "sinal"),
        [
            ({"enforcement": "disabled"}, "`enforcement` = `disabled`"),
            ({"gate": False}, "fora dos required checks"),
            ({"strict": False}, "`strict` desligado"),
        ],
    )
    def test_gate_enfraquecido_alarma(self, estado: dict, sinal: str) -> None:
        _, run = self._tripwire(ruleset=ruleset(admin=False, **estado))
        assert "enfraqueceu o gate" in _creates(run)[0] and sinal in _creates(run)[0]

    def test_gate_enfraquecido_com_issue_fechada_e_reaberto(self) -> None:
        chave = "ruleset-updated=2026-10-09T15:53:52.112+00:00"
        _, run = self._tripwire(
            ruleset=ruleset(admin=False, enforcement="disabled"),
            issues=[incident(chave, number=77, state="closed")],
        )
        assert run.writes[0].startswith("issue reopen 77")

    def test_erro_de_api_e_nao_medido(self, capsys: Any) -> None:
        rc, run = self._tripwire(ruleset_error="gh api: Bad Gateway (HTTP 502)")
        assert rc == 2 and run.writes == [] and "NÃO MEDIDO" in capsys.readouterr().err
