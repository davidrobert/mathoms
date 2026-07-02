"""A27.l1 slice 1 (ADR-293) — resolver de chave natural de folha de LISTA citada."""

from __future__ import annotations

from backend.app.services.parecer_citation_lineage import resolve_citation_natural_key

_ATIVO_DONOS = {"PETR4": ("Ana", "XP"), "ITSA4": ("Bruno", "Itau"), "MXRF11": ("Ana", "Rico")}


def _ativo(i: int, nome: str) -> dict:
    membro, instituicao = _ATIVO_DONOS[nome]
    return {
        "posicao": i,
        "nome": nome,
        "membro": membro,
        "instituicao": instituicao,
        "valor": 100 - i,
    }


def _e5_with_top_ativos(order: list[str]) -> dict:
    """E5 sintético: top_ativos na ordem dada (nome = elemento), posicao = índice."""
    return {"investimentos": {"top_ativos": [_ativo(i, n) for i, n in enumerate(order)]}}


def test_top_ativo_natural_key_is_content_based() -> None:
    e5 = _e5_with_top_ativos(["PETR4", "ITSA4", "MXRF11"])
    key = resolve_citation_natural_key(e5, "$.investimentos.top_ativos[0].valor")
    assert key == "membro=Ana|instituicao=XP|nome=PETR4|posicao=0"


def test_top_ativo_same_item_stable_across_reorder() -> None:
    """KR3: o MESMO ativo produz chave idêntica (fora posicao) em qualquer posição."""
    run_r = _e5_with_top_ativos(["PETR4", "ITSA4", "MXRF11"])
    run_r1 = _e5_with_top_ativos(["MXRF11", "PETR4", "ITSA4"])  # rebaseline reordenou
    # PETR4 está em [0] no run R e em [1] no run R+1 — a parte de identidade é a mesma.
    k_r = resolve_citation_natural_key(run_r, "$.investimentos.top_ativos[0].valor")
    k_r1 = resolve_citation_natural_key(run_r1, "$.investimentos.top_ativos[1].valor")
    assert k_r.split("|posicao=")[0] == k_r1.split("|posicao=")[0]
    assert k_r.startswith("membro=Ana|instituicao=XP|nome=PETR4")
    assert k_r1.startswith("membro=Ana|instituicao=XP|nome=PETR4")


def test_index_endereca_ativo_diferente_apos_reorder() -> None:
    """Prova o porquê do slice: o índice [0] aponta para ativo DIFERENTE após reorder."""
    run_r = _e5_with_top_ativos(["PETR4", "ITSA4", "MXRF11"])
    run_r1 = _e5_with_top_ativos(["MXRF11", "PETR4", "ITSA4"])
    assert resolve_citation_natural_key(run_r, "$.investimentos.top_ativos[0].valor") != (
        resolve_citation_natural_key(run_r1, "$.investimentos.top_ativos[0].valor")
    )


def test_alocacao_por_classe_natural_key() -> None:
    e5 = {
        "alocacao_por_classe": [
            {"classe": "Renda Fixa", "valor": 500},
            {"classe": "Ações", "valor": 300},
        ]
    }
    assert resolve_citation_natural_key(e5, "$.alocacao_por_classe[1].valor") == "classe=Ações"


def test_scalar_path_returns_none() -> None:
    """Folha escalar (sem [i]) é estável por path — dispensa chave natural."""
    e5 = {"reserva_emergencia": {"saldo_liquido": 12000}}
    assert resolve_citation_natural_key(e5, "$.reserva_emergencia.saldo_liquido") is None


def test_unresolvable_path_returns_none() -> None:
    e5 = {
        "investimentos": {
            "top_ativos": [{"posicao": 0, "nome": "X", "membro": "A", "instituicao": "B"}]
        }
    }
    assert resolve_citation_natural_key(e5, "$.investimentos.top_ativos[9].valor") is None
    assert resolve_citation_natural_key(e5, "$.nao.existe[0].valor") is None


def test_list_item_without_known_key_returns_none() -> None:
    e5 = {"foo": {"bar": [{"qualquer": 1, "valor": 2}]}}
    assert resolve_citation_natural_key(e5, "$.foo.bar[0].valor") is None
