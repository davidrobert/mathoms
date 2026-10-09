"""Tests — ``_find_top_asset`` lê ``e5_data["investimentos"]["top_ativos"][0]``.

Cutover: deixou de ler ``processed/E4_unified/investimentos-4_unified.json``
e passou a ler o campo canônico produzido pelo TopAtivosAnalyzer no E5.
Garante coerência com ``patrimonio_investivel`` (mesmo ``bens_por_membro``).
"""

from __future__ import annotations

from scripts.generate_narratives import _abstract_asset_nome, _find_top_asset

_FIRST = {
    "posicao": 1,
    "nome": "Tesouro IPCA+ 2045",
    "valor": 300_000.0,
    "membro": "david",
    "instituicao": "Btg",
}
_SECOND = {"posicao": 2, "nome": "ITSA4", "valor": 150_000, "membro": "mariana"}


_VAZIO = {
    "nome": "",
    "valor": 0,
    "membro": "",
    "instituicao": "",
    "sem_peso": False,
    "desconhecido": False,
}


def test_returns_first_item_of_top_ativos():
    out = _find_top_asset({"investimentos": {"top_ativos": [_FIRST, _SECOND]}})
    esperado = {k: _FIRST[k] for k in ("nome", "valor", "membro", "instituicao")}
    assert out == esperado | {"sem_peso": False, "desconhecido": False}


def test_returns_empty_when_top_ativos_missing():
    assert _find_top_asset({"investimentos": {}}) == _VAZIO


def test_returns_empty_when_top_ativos_is_empty_list():
    assert _find_top_asset({"investimentos": {"top_ativos": []}}) == _VAZIO


def test_returns_empty_when_investimentos_block_missing():
    assert _find_top_asset({}) == _VAZIO


# [[ADR-444]] D4/D5: a prosa do narrador lê do payload se o #1 tem peso e se o uso dele é
# conhecido — o mesmo que o card do ranking lê.
def test_marca_o_topo_sem_peso():
    topo = _FIRST | {"pct_carteira": None, "classificacao_imovel": "desconhecido"}
    out = _find_top_asset({"investimentos": {"top_ativos": [topo]}})
    assert out["sem_peso"] is True
    assert out["desconhecido"] is True


def test_marca_o_topo_desconhecido_com_peso():
    topo = _FIRST | {"pct_carteira": 30.0, "classificacao_imovel": "desconhecido"}
    out = _find_top_asset({"investimentos": {"top_ativos": [topo]}})
    assert out["sem_peso"] is False
    assert out["desconhecido"] is True


# Fixture sintética (sem PII real — ADR-319): apenas as PALAVRAS-marcador que a
# abstração deve cortar; nenhum CNPJ/IPTU/endereço/matrícula em formato real.
_RAW_REGISTRAL = (
    "APARTAMENTO NO CONDOMINIO EXEMPLO. CNPJ da incorporadora informado no laudo. "
    "Inscrição municipal (IPTU) informada. AV das Amostras, sem numero. Matrícula sintética."
)


def test_abstract_asset_nome_strips_registral_pii():
    out = _abstract_asset_nome(_RAW_REGISTRAL, "Imóveis Investimento")
    for marker in ("CNPJ", "Matríc", "IPTU", "Inscri", "AV "):
        assert marker not in out, f"vazou marcador registral: {marker!r}"
    assert out and len(out) <= 60


def test_abstract_asset_nome_keeps_clean_financial_label():
    assert _abstract_asset_nome("Tesouro IPCA+ 2045", "Renda Fixa") == "Tesouro IPCA+ 2045"


def test_abstract_asset_nome_empty_falls_back_to_classe():
    assert _abstract_asset_nome("", "Imóveis") == "Imóveis"


def test_find_top_asset_abstracts_registral_nome():
    out = _find_top_asset(
        {
            "investimentos": {
                "top_ativos": [
                    {
                        "nome": _RAW_REGISTRAL,
                        "valor": 900_000.0,
                        "membro": "david",
                        "instituicao": "",
                        "classe": "Imóveis Investimento",
                    }
                ]
            }
        }
    )
    assert "CNPJ" not in out["nome"] and "Matríc" not in out["nome"] and "IPTU" not in out["nome"]
    assert out["valor"] == 900_000.0


def test_no_longer_reads_e4_disk_artifact(tmp_path, monkeypatch):
    # Garante que a função NÃO depende mais do arquivo
    # processed/E4_unified/investimentos-4_unified.json — leitura de disco
    # foi substituída por leitura do dict e5_data.
    import scripts.generate_narratives as mod

    monkeypatch.setattr(mod, "PROJECT_DIR", tmp_path)
    e5_data = {
        "investimentos": {
            "top_ativos": [{"nome": "X", "valor": 1.0, "membro": "y", "instituicao": "Z"}]
        }
    }
    out = _find_top_asset(e5_data)
    assert out["nome"] == "X"
