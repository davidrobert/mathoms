"""Tests — ``_extract_top_institutions`` lê ``e5_data["investimentos"]["instituicoes_por_membro"]`` + ``n_imoveis_total`` (fonte canônica InstituicoesPorMembroAnalyzer; substituiu leitura legacy de E4 disk artifacts)."""

from __future__ import annotations

import scripts.e5n_narrativas as mod
from scripts.e5n_narrativas import _extract_top_institutions

_FAMILY = {
    "titular": "david",
    "membros": {
        "david": {"papel": "titular", "nome_curto": "David"},
        "mariana": {"papel": "conjuge", "nome_curto": "Mariana"},
    },
}


def _e5(*entries, n_imoveis=0):
    return {
        "investimentos": {
            "instituicoes_por_membro": [
                {"membro": m, "instituicoes": insts} for m, insts in entries
            ],
            "n_imoveis_total": n_imoveis,
        }
    }


def test_returns_titular_and_conjuge_lists(monkeypatch):
    monkeypatch.setattr(mod, "FAMILY", _FAMILY)
    e5 = _e5(("david", ["Btg", "Itau"]), ("mariana", ["Xp"]), n_imoveis=2)
    out = _extract_top_institutions(e5)
    assert out == {
        "titular_inst": ["Btg", "Itau"],
        "conjuge_inst": ["Xp"],
        "n_imoveis": 2,
    }


def test_returns_empty_when_block_missing(monkeypatch):
    monkeypatch.setattr(mod, "FAMILY", _FAMILY)
    out = _extract_top_institutions({})
    assert out == {"titular_inst": [], "conjuge_inst": [], "n_imoveis": 0}


def test_returns_empty_when_member_absent(monkeypatch):
    monkeypatch.setattr(mod, "FAMILY", _FAMILY)
    e5 = _e5(("mariana", ["Xp"]))
    out = _extract_top_institutions(e5)
    assert out["titular_inst"] == []
    assert out["conjuge_inst"] == ["Xp"]


def test_no_conjuge_in_family(monkeypatch):
    monkeypatch.setattr(
        mod,
        "FAMILY",
        {"titular": "david", "membros": {"david": {"papel": "titular"}}},
    )
    e5 = _e5(("david", ["Btg"]))
    out = _extract_top_institutions(e5)
    assert out["titular_inst"] == ["Btg"]
    assert out["conjuge_inst"] == []


def test_no_longer_reads_disk(tmp_path, monkeypatch):
    # Garante que a função NÃO depende mais dos arquivos
    # processed/E4_unified/investimentos-4_unified.json e patrimonio-4_unified.json.
    monkeypatch.setattr(mod, "PROJECT_DIR", tmp_path)
    monkeypatch.setattr(mod, "FAMILY", _FAMILY)
    e5 = _e5(("david", ["Btg"]), n_imoveis=1)
    out = _extract_top_institutions(e5)
    assert out["titular_inst"] == ["Btg"]
    assert out["n_imoveis"] == 1
