"""Ano-base por classe + estado ternário de imóvel ([[ADR-433]]): o run `U5` tinha
saldo de 2026 e imóveis/dívidas de 2025, a eleição por união escolhia 2026, e as
classes que param em 2025 projetavam 0,00 — publicando família sem casa nem dívida."""

from __future__ import annotations

import pytest

from pipeline.domain.services.patrimonio_imovel_classifier import (
    CLASSIFICATION_DESCONHECIDO,
    CLASSIFICATION_RESIDENCIA_PRINCIPAL,
    classificacao_do_imovel,
    cobertura_classificacao_imovel,
    split_imoveis_geradores_vs_nao_geradores,
    split_imoveis_with_overrides,
)
from pipeline.domain.services.patrimonio_resolvers import (
    anos_base_por_classe,
    anos_base_por_membro,
    build_members_from_consolidated,
)
from pipeline.domain.services.patrimonio_types import MemberIdentity

_PID_CASA = "pid-casa"


@pytest.fixture
def identity() -> MemberIdentity:
    return MemberIdentity(
        titular_key="david", conjuge_key="mariana", titular_nome="David", conjuge_nome="Mariana"
    )


_IMOVEIS_2025 = [
    {
        "proprietario": "david",
        "descricao": "Casa",
        "property_id": _PID_CASA,
        "valores_31_12": {"2025": 996821.46},
    },
    {
        "proprietario": "david",
        "descricao": "Apartamento sem identidade",
        "valores_31_12": {"2025": 350000.0},
    },
]
_VEICULOS_2025 = [
    {"proprietario": "david", "descricao": "Carro", "valores_31_12": {"2025": 40000.0}}
]
_DIVIDAS_2025 = [
    {"proprietario": "david", "descricao": "Financiamento", "saldo_31_12": {"2025": 230459.13}}
]
# O investimento é a única classe que alcança 2026, e é ele que sequestrava o ano
# das outras três na eleição por união.
_INVESTIMENTOS_2026 = [
    {"proprietario": "david", "descricao": "CDB", "valores_31_12": {"2026": 116374.26}}
]


@pytest.fixture
def baseline_com_investimento_adiantado() -> dict:
    """A forma do corpus que produziu o defeito no run `U5`."""
    return {
        "patrimonio_por_ano": {"2026": {"total_bens": 0, "total_dividas": 0}},
        "imoveis_consolidados": _IMOVEIS_2025,
        "veiculos_consolidados": _VEICULOS_2025,
        "dividas": _DIVIDAS_2025,
        "investimentos_consolidados": _INVESTIMENTOS_2026,
    }


def test_ano_e_eleito_dentro_da_classe_nao_sobre_a_uniao(
    baseline_com_investimento_adiantado, identity
):
    """O 2026 do investimento não sequestra o ano de imóveis/veículos/dívidas."""
    titular, _ = anos_base_por_classe(baseline_com_investimento_adiantado, identity, "2026")
    assert titular.para("imoveis") == "2025"
    assert titular.para("veiculos") == "2025"
    assert titular.para("dividas") == "2025"
    assert titular.para("investimentos") == "2026"


def test_a_eleicao_por_uniao_e_o_defeito_reproduzido(baseline_com_investimento_adiantado, identity):
    # Sem esta asserção o teste acima passaria mesmo que a correção fosse inerte:
    # ele afirmaria o novo produtor sem provar que ele difere do velho.
    """Não-inércia: o produtor ANTIGO ainda elege 2026 para todas as classes."""
    ano_titular, _ = anos_base_por_membro(baseline_com_investimento_adiantado, identity, "2026")
    assert ano_titular == "2026"


def test_residencia_e_divida_nao_projetam_zero(baseline_com_investimento_adiantado, identity):
    """Os três baldes que o run publicou como zero voltam com o valor declarado."""
    titular, _ = build_members_from_consolidated(baseline_com_investimento_adiantado, identity)
    bens = titular["bens"]
    residencia, outros = split_imoveis_with_overrides(
        titular_bens=bens,
        conjuge_bens={},
        overrides_by_property_id={_PID_CASA: CLASSIFICATION_RESIDENCIA_PRINCIPAL},
    )
    assert residencia == pytest.approx(996821.46)
    assert outros == pytest.approx(350000.0)
    assert titular["total_dividas"] == pytest.approx(230459.13)
    assert sum(v["valor_31_12_ano_base"] for v in bens["veiculos"]) == pytest.approx(40000.0)


def test_ano_base_publicado_e_o_menor_com_o_mapa_ao_lado(
    baseline_com_investimento_adiantado, identity
):
    """Escalar nunca superestima frescor; o mapa por classe viaja junto (ADR-383 §6)."""
    titular, _ = build_members_from_consolidated(baseline_com_investimento_adiantado, identity)
    assert titular["ano_base"] == "2025"
    assert titular["ano_base_por_classe"]["investimentos"] == "2026"


def test_credito_de_residuo_nao_dispara_com_classes_em_anos_distintos(
    baseline_com_investimento_adiantado, identity
):
    """Com sintético multi-ano, creditar a diferença ao titular fabrica patrimônio."""
    baseline = dict(baseline_com_investimento_adiantado)
    baseline["patrimonio_por_ano"] = {"2026": {"total_bens": 9_000_000.0, "total_dividas": 0}}
    titular, _ = build_members_from_consolidated(baseline, identity)
    assert titular["total_bens"] < 9_000_000.0


# ---------------------------------------------------------------------------
# Estado ternário — `pid` ausente não é "não é residência" ([[ADR-433]] §D3)
# ---------------------------------------------------------------------------


def test_imovel_sem_property_id_e_desconhecido_nao_nao_residencia():
    assert classificacao_do_imovel({}, {}) == CLASSIFICATION_DESCONHECIDO
    assert (
        classificacao_do_imovel({"property_id": "pid-x"}, {}) == CLASSIFICATION_DESCONHECIDO
    ), "id sem rótulo também é desconhecido — não é 'não é residência'"


def test_cobertura_mede_valor_porque_a_contagem_mente():
    """8 de 9 por contagem, 57% por valor: a residência é o maior item isolado."""
    bens = {
        "imoveis": [
            {"property_id": _PID_CASA, "valores_31_12": {"2025": 996821.46}},
            *({"valores_31_12": {"2025": 167984.60}} for _ in range(8)),
        ]
    }
    for im in bens["imoveis"]:
        im["valor_31_12_ano_base"] = list(im["valores_31_12"].values())[0]
    cobertura = cobertura_classificacao_imovel(
        titular_bens=bens,
        conjuge_bens={},
        overrides_by_property_id={_PID_CASA: CLASSIFICATION_RESIDENCIA_PRINCIPAL},
    )
    assert (cobertura.n_desconhecido, cobertura.n_total) == (8, 9)
    assert cobertura.pct_desconhecido == pytest.approx(57.4, abs=0.5)


def test_a_particao_monetaria_nao_se_move_com_o_estado_ternario():
    """[[ADR-420]] §D2 intacta: nomear o desconhecido não o tira do lado conservador."""
    bens = {
        "imoveis": [
            {"property_id": _PID_CASA, "valor_31_12_ano_base": 100.0},
            {"valor_31_12_ano_base": 300.0},
        ]
    }
    overrides = {_PID_CASA: CLASSIFICATION_RESIDENCIA_PRINCIPAL}
    residencia, outros = split_imoveis_with_overrides(
        titular_bens=bens, conjuge_bens={}, overrides_by_property_id=overrides
    )
    geradores, nao_geradores = split_imoveis_geradores_vs_nao_geradores(
        titular_bens=bens, conjuge_bens={}, overrides_by_property_id=overrides
    )
    assert (residencia, outros) == (100.0, 300.0)
    assert (geradores, nao_geradores) == (0.0, 300.0)
