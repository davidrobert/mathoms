"""Tests — ``_find_top_asset`` lê ``e5_data["investimentos"]["top_ativos"][0]``.

Cutover: deixou de ler ``processed/E4_unified/investimentos-4_unified.json``
e passou a ler o campo canônico produzido pelo TopAtivosAnalyzer no E5.
Garante coerência com ``patrimonio_investivel`` (mesmo ``bens_por_membro``).
"""

from __future__ import annotations

from scripts.e5n_narrativas import _find_top_asset

_FIRST = {
    "posicao": 1,
    "nome": "Tesouro IPCA+ 2045",
    "valor": 300_000.0,
    "membro": "david",
    "instituicao": "Btg",
}
_SECOND = {"posicao": 2, "nome": "ITSA4", "valor": 150_000, "membro": "mariana"}


def test_returns_first_item_of_top_ativos():
    out = _find_top_asset({"investimentos": {"top_ativos": [_FIRST, _SECOND]}})
    assert out == {k: _FIRST[k] for k in ("nome", "valor", "membro", "instituicao")}


def test_returns_empty_when_top_ativos_missing():
    out = _find_top_asset({"investimentos": {}})
    assert out == {"nome": "", "valor": 0, "membro": "", "instituicao": ""}


def test_returns_empty_when_top_ativos_is_empty_list():
    out = _find_top_asset({"investimentos": {"top_ativos": []}})
    assert out == {"nome": "", "valor": 0, "membro": "", "instituicao": ""}


def test_returns_empty_when_investimentos_block_missing():
    out = _find_top_asset({})
    assert out == {"nome": "", "valor": 0, "membro": "", "instituicao": ""}


def test_no_longer_reads_e4_disk_artifact(tmp_path, monkeypatch):
    # Garante que a função NÃO depende mais do arquivo
    # processed/E4_unified/investimentos-4_unified.json — leitura de disco
    # foi substituída por leitura do dict e5_data.
    import scripts.e5n_narrativas as mod

    monkeypatch.setattr(mod, "PROJECT_DIR", tmp_path)
    e5_data = {
        "investimentos": {
            "top_ativos": [{"nome": "X", "valor": 1.0, "membro": "y", "instituicao": "Z"}]
        }
    }
    out = _find_top_asset(e5_data)
    assert out["nome"] == "X"
