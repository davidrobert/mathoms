"""ADR-375 — travessia da cadeia de supersessão (função pura, sem DB)."""

from __future__ import annotations

from datetime import datetime, timezone

from backend.app.services.supersession_chain import (
    MAX_CHAIN_DEPTH,
    resolve_supersession_chain,
)

_T = datetime(2026, 8, 11, tzinfo=timezone.utc)


def _live() -> tuple[None, None]:
    return (None, None)


def _superseded_by(winner_id: str) -> tuple[datetime, str]:
    return (_T, winner_id)


def test_row_viva_devolve_ela_mesma():
    assert resolve_supersession_chain("a", {"a": _live()}) == "a"


def test_um_salto_chega_na_vencedora():
    links = {"perdedora": _superseded_by("vencedora"), "vencedora": _live()}
    assert resolve_supersession_chain("perdedora", links) == "vencedora"


def test_cadeia_de_tres_saltos_chega_na_ponta_viva():
    links = {
        "a": _superseded_by("b"),
        "b": _superseded_by("c"),
        "c": _superseded_by("d"),
        "d": _live(),
    }
    assert resolve_supersession_chain("a", links) == "d"


def test_ponteiro_orfao_pula_o_candidato():
    """superseded_at setado + superseded_by_id NULL (ON DELETE SET NULL)."""
    links = {"orfa": (_T, None)}
    assert resolve_supersession_chain("orfa", links) is None


def test_ciclo_nao_trava_e_pula_o_candidato():
    links = {"a": _superseded_by("b"), "b": _superseded_by("a")}
    assert resolve_supersession_chain("a", links) is None


def test_auto_referencia_pula_o_candidato():
    links = {"a": _superseded_by("a")}
    assert resolve_supersession_chain("a", links) is None


def test_cadeia_mais_longa_que_o_cap_pula_o_candidato():
    ids = [f"n{i}" for i in range(MAX_CHAIN_DEPTH + 3)]
    links = {cur: _superseded_by(nxt) for cur, nxt in zip(ids, ids[1:])}
    links[ids[-1]] = _live()
    assert resolve_supersession_chain(ids[0], links) is None


def test_cadeia_exatamente_no_cap_ainda_resolve():
    ids = [f"n{i}" for i in range(MAX_CHAIN_DEPTH)]
    links = {cur: _superseded_by(nxt) for cur, nxt in zip(ids, ids[1:])}
    links[ids[-1]] = _live()
    assert resolve_supersession_chain(ids[0], links) == ids[-1]


def test_ponteiro_para_row_desconhecida_pula_o_candidato():
    links = {"a": _superseded_by("fora-do-workspace")}
    assert resolve_supersession_chain("a", links) is None


def test_row_desconhecida_pula_o_candidato():
    assert resolve_supersession_chain("nao-existe", {}) is None
