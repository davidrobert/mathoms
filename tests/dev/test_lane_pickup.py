"""Testes de `dev/lane_pickup.py` — a sonda de ocupação viva.

O veredito é a parte que decide pickup, e ela é pura: recebe frontmatter +
deps pendentes + sinais. Os sinais vêm de git e são injetados, não mockados
com MagicMock (CLAUDE.md §Testes: fakes nomeados).

O caso de origem é o da A40.l35 em 2026-08-13: frontmatter `open`, sem branch
remota, sem PR — e uma sessão viva num worktree há 2h.
"""

from __future__ import annotations

import pytest

from dev import lane_pickup
from dev.lane_pickup import Occupancy, _pending_deps, _verdict

_OCUPADA = [Occupancy("worktree", "a40-l35-bundle [agent/...] · 20 arq. sujos")]


def test_ocupacao_vence_qualquer_status() -> None:
    # A l35 dizia `open` e sem dep pendente. O sinal de worktree é o único que
    # a contradiz — e tem de vencer, senão a sonda repete o erro da superfície.
    assert _verdict({"status": "open"}, [], _OCUPADA).startswith("OCUPADA")


def test_livre_quando_open_sem_dep_e_sem_sinal() -> None:
    assert _verdict({"status": "open"}, [], []) == "LIVRE"


def test_planned_nao_e_pegavel() -> None:
    assert _verdict({"status": "planned"}, [], []).startswith("NÃO LIBERADA")


@pytest.mark.parametrize("status", ["shipped", "cancelled"])
def test_terminal_nao_tem_o_que_pegar(status: str) -> None:
    assert _verdict({"status": status}, [], []).startswith("TERMINAL")


def test_dep_pendente_bloqueia() -> None:
    assert _verdict({"status": "open"}, ["A40.l5 (in_progress)"], []).startswith("BLOQUEADA")


def test_amarra_parcial_destrava_dep_pendente() -> None:
    verdict = _verdict({"status": "open", "partial_delivery": True}, ["A40.l5 (in_progress)"], [])
    assert verdict.startswith("PEGÁVEL COM AMARRA PARCIAL")


def test_pending_deps_ignora_dep_terminal_e_desconhecida() -> None:
    lanes = {"A1.l1": {"status": "shipped"}, "A1.l2": {"status": "open"}}
    front = {"depends_on": ["[[A1.l1]]", "[[A1.l2]]", "[[A1.l404]]"]}
    assert _pending_deps(front, lanes) == ["A1.l2 (open)"]


def test_pending_deps_aceita_wikilink_com_apelido() -> None:
    lanes = {"A1.l1": {"status": "open"}}
    assert _pending_deps({"depends_on": ["[[A1.l1|a primeira]]"]}, lanes) == ["A1.l1 (open)"]


def test_id_ausente_sem_sinal_e_id_livre(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(lane_pickup, "occupancy_signals", lambda *_: [])
    text, code = lane_pickup._report_unknown("A40.l99")
    assert "id livre" in text
    assert code == 2


def test_id_ausente_com_sinal_avisa_para_nao_realocar(monkeypatch: pytest.MonkeyPatch) -> None:
    # §Pendência 13 da A40: 8 renumerações numa sessão porque `ls` local mede
    # o teto errado enquanto outra sessão segura o id sem commitar.
    monkeypatch.setattr(
        lane_pickup, "occupancy_signals", lambda *_: [Occupancy("branch", "agent/a40-l61-x/2026")]
    )
    text, code = lane_pickup._report_unknown("A40.l61")
    assert "TOMADO" in text
    assert code == 1
