"""Off-by-one exercício↔ano-base no consolidador E1.5c→E5: trava a regressão que zerava imóveis/veículos (ADR-274)."""

from __future__ import annotations

import logging

import pytest

import scripts.consolidate_baseline as e15
from pipeline.domain.services.e5_member_resolver import (
    E5MemberResolver,
    MemberResolverConfig,
)
from pipeline.domain.services.patrimonio_resolvers import (
    _resolve_ano_ref,
    _resolve_summary_year,
    build_members_from_consolidated,
)
from pipeline.domain.services.patrimonio_types import (
    MemberIdentity,
    _max_value_year,
    resolve_value_year,
)

_DAVID = MemberIdentity(
    titular_key="david", conjuge_key="mariana", titular_nome="David", conjuge_nome="Mariana"
)
_LOGGER_NAME = "mathoms.pipeline.patrimonio"


def _divergent_baseline() -> dict:
    """Artefato legado: itens em 2024, resumo chaveado em 2025 (exercício)."""
    return {
        "imoveis_consolidados": [
            {
                "descricao": "Casa",
                "codigo_rfb": "12",
                "proprietario": "david",
                "valores_31_12": {"2024": 500_000.0},
            }
        ],
        "veiculos_consolidados": [
            {"descricao": "Carro", "proprietario": "david", "valores_31_12": {"2024": 80_000.0}}
        ],
        "patrimonio_por_ano": {"2025": {"total_bens": 580_000.0, "total_dividas": 0.0}},
    }


# =============================================================================
# _max_value_year
# =============================================================================


def test_max_value_year_plain_year():
    assert _max_value_year(_divergent_baseline()) == "2024"


def test_max_value_year_ignores_sentinel():
    baseline = {"imoveis_consolidados": [{"valores_31_12": {"999999": 1, "2023": 2}}]}
    assert _max_value_year(baseline) == "2023"


def test_max_value_year_legacy_31_12_format():
    baseline = {"investimentos_consolidados": [{"valores_31_12": {"31_12_2022": 1}}]}
    assert _max_value_year(baseline) == "2022"


def test_max_value_year_empty_returns_none():
    assert _max_value_year({"imoveis_consolidados": [{"valor": 5}]}) is None
    assert _max_value_year({}) is None


def test_max_value_year_scans_dividas_saldo():
    baseline = {"dividas": [{"saldo_31_12": {"2024": 100_000}}]}
    assert _max_value_year(baseline) == "2024"


def test_max_value_year_picks_global_max_across_lists():
    baseline = {
        "imoveis_consolidados": [{"valores_31_12": {"2022": 1}}],
        "veiculos_consolidados": [{"valores_31_12": {"2024": 2}}],
    }
    assert _max_value_year(baseline) == "2024"


# =============================================================================
# resolve_value_year — warning tipado
# =============================================================================


def test_resolve_value_year_warns_on_divergence(caplog):
    with caplog.at_level(logging.WARNING, logger=_LOGGER_NAME):
        value_year = resolve_value_year(_divergent_baseline(), summary_year="2025")
    assert value_year == "2024"
    assert any("divergente" in r.getMessage() for r in caplog.records)
    rec = next(r for r in caplog.records if "divergente" in r.getMessage())
    assert rec.value_year == "2024"
    assert rec.summary_year == "2025"


def test_resolve_value_year_silent_when_aligned(caplog):
    aligned = {
        "imoveis_consolidados": [{"valores_31_12": {"2024": 500_000.0}}],
        "patrimonio_por_ano": {"2024": {"total_bens": 500_000.0, "total_dividas": 0.0}},
    }
    with caplog.at_level(logging.WARNING, logger=_LOGGER_NAME):
        value_year = resolve_value_year(aligned, summary_year="2024")
    assert value_year == "2024"
    assert not [r for r in caplog.records if "divergente" in r.getMessage()]


def test_resolve_value_year_falls_back_to_summary_when_no_items():
    assert resolve_value_year({}, summary_year="2024") == "2024"


# =============================================================================
# _resolve_ano_ref — desacoplamento value_year vs summary_year
# =============================================================================


def test_resolve_ano_ref_decouples_value_from_summary():
    res = _resolve_ano_ref(_divergent_baseline())
    assert res.value_year == "2024"  # ano-base dos itens
    assert res.summary_year == "2025"  # chave de patrimonio_por_ano (exercício)
    # total_bens vem do resumo pela chave própria (summary_year), não do AnoResolution.
    summary_year, total_bens, _ = _resolve_summary_year(_divergent_baseline())
    assert summary_year == "2025"
    assert total_bens == 580_000.0


# =============================================================================
# build_members_from_consolidated — regressão do zero
# =============================================================================


def test_consolidated_imoveis_not_zeroed_on_divergence():
    titular, _conjuge = build_members_from_consolidated(_divergent_baseline(), _DAVID)
    imoveis = titular["bens"]["imoveis"]
    veiculos = titular["bens"]["veiculos"]
    assert imoveis[0]["valor_31_12_ano_base"] == 500_000.0
    assert veiculos[0]["valor_31_12_ano_base"] == 80_000.0


# =============================================================================
# E5MemberResolver — segundo path com o mesmo bug
# =============================================================================


def test_member_resolver_not_zeroed_on_divergence():
    r = E5MemberResolver(MemberResolverConfig(titular_key="david", conjuge_key="mariana")).resolve(
        _divergent_baseline()
    )
    assert r.reference_year == "2024"  # ano-base, não exercício
    assert r.titular_data["bens"]["imoveis"][0]["valor_31_12_ano_base"] == 500_000.0


# =============================================================================
# Layer 2 — consolidate_from_itens chaveia em ano-base
# =============================================================================


def _imovel_item(valor_brl, ano: int) -> dict:
    return {
        "codigo": "12",
        "descricao": "Casa",
        "categoria": "imovel",
        "valor_brl": valor_brl,
        "membro": "david",
        "ano": ano,
    }


def _itens_baseline(*itens: dict) -> dict:
    return {"itens": list(itens), "resumo": {"total_ativos": 500_000.0, "ano_referencia": 2025}}


def test_consolidate_from_itens_keys_by_ano_base_not_exercicio():
    out = e15.consolidate_from_itens(_itens_baseline(_imovel_item(500_000.0, 2024)))
    assert list(out["patrimonio_por_ano"].keys()) == ["2024"]
    assert out["imoveis_consolidados"][0]["ano_referencia"] == 2024
    assert list(out["imoveis_consolidados"][0]["valores_31_12"].keys()) == ["2024"]


def test_layer2_artifact_produces_no_divergence_warning(caplog):
    out = e15.consolidate_from_itens(_itens_baseline(_imovel_item(500_000.0, 2024)))
    with caplog.at_level(logging.WARNING, logger=_LOGGER_NAME):
        res = _resolve_ano_ref(out)
    assert res.value_year == res.summary_year == "2024"
    assert not [r for r in caplog.records if "divergente" in r.getMessage()]


def test_consolidate_from_itens_multi_year_does_not_double():
    """Multi-ano (2023+2024): value_year=max=2024; total não soma 2023+2024."""
    out = e15.consolidate_from_itens(
        _itens_baseline(_imovel_item(480_000.0, 2023), _imovel_item(500_000.0, 2024))
    )
    assert list(out["patrimonio_por_ano"].keys()) == ["2024"]
    res = _resolve_ano_ref(out)
    assert res.value_year == "2024"
    titular, _ = build_members_from_consolidated(out, _DAVID)
    total_imoveis = sum(i["valor_31_12_ano_base"] for i in titular["bens"]["imoveis"])
    # Só o valor 2024 de cada série conta — não 480k + 500k.
    assert total_imoveis == 500_000.0


# =============================================================================
# Eixo de ano POR MEMBRO (A40.l69 · ADR-394)
#
# `_max_value_year` escolhe um ano para o domicílio inteiro. Com os cônjuges
# declarando em anos disjuntos, quem não tem item no ano escolhido cai no
# fallback de `_resolve_item_valor` e vira 0,00 — a conflação `null`↔`0,00`
# que a ADR-394 proíbe um andar acima. Medido no corpus: 5/5 runs recentes.
# =============================================================================


def _baseline_anos_disjuntos() -> dict:
    """Titular declara em 2025, cônjuge em 2023 — nenhum ano em comum."""
    return {
        "investimentos_consolidados": [
            {"descricao": "CDB", "proprietario": "david", "valores_31_12": {"2025": 900_000.0}},
            {"descricao": "FII", "proprietario": "mariana", "valores_31_12": {"2023": 110_000.0}},
        ],
        # v1: o resumo é de UM ano — é o que torna o top-up perigoso cross-ano.
        "patrimonio_por_ano": {"2025": {"total_bens": 900_000.0}},
    }


def test_anos_disjuntos_valoram_os_dois_membros():
    """O defeito: o ano do domicílio zerava quem não declarou nele."""
    titular, conjuge = build_members_from_consolidated(_baseline_anos_disjuntos(), _DAVID)
    assert titular["bens"]["investimentos"][0]["valor_31_12_ano_base"] == 900_000.0
    assert conjuge["bens"]["investimentos"][0]["valor_31_12_ano_base"] == 110_000.0


def test_o_defeito_e_do_eixo_e_nao_do_conjuge():
    """Simetria: com o ano do domicílio forçado a 2023, quem zerava era o TITULAR."""
    baseline = _baseline_anos_disjuntos()
    assert _max_value_year(baseline) == "2025"
    # Sob o eixo único, cada membro só é valorado no ano que o domicílio escolheu.
    titular_2023, conjuge_2023 = _split_no_ano(baseline, "2023")
    titular_2025, conjuge_2025 = _split_no_ano(baseline, "2025")
    assert (titular_2023, conjuge_2023) == (0.0, 110_000.0)
    assert (titular_2025, conjuge_2025) == (900_000.0, 0.0)


def _split_no_ano(baseline: dict, ano: str) -> tuple[float, float]:
    """Total de investimentos de cada membro resolvido num ano único."""
    from pipeline.domain.services.patrimonio_resolvers import _split_investimentos

    titular, conjuge = _split_investimentos(baseline, _DAVID, ano)
    soma = lambda itens: sum(i["valor_31_12_ano_base"] for i in itens)  # noqa: E731
    return soma(titular), soma(conjuge)


def test_ano_base_por_membro_carimbado_no_dict():
    """Soma cross-ano não pode ser silenciosa (ADR-383 §6)."""
    titular, conjuge = build_members_from_consolidated(_baseline_anos_disjuntos(), _DAVID)
    assert (titular["ano_base"], conjuge["ano_base"]) == ("2025", "2023")


def test_top_up_do_titular_nao_dispara_com_anos_disjuntos():
    """`total_bens_summary` é de um ano só; com anos distintos o resíduo fabricaria patrimônio."""
    titular, _ = build_members_from_consolidated(_baseline_anos_disjuntos(), _DAVID)
    # Sem a guarda, o titular receberia `900k - (900k + 110k) = -110k` do top-up.
    assert titular["total_bens"] == 900_000.0


def test_top_up_do_titular_segue_vivo_com_ano_unico():
    """A guarda é sobre anos disjuntos — o comportamento legado não muda no caso comum."""
    baseline = {
        "investimentos_consolidados": [
            {"descricao": "CDB", "proprietario": "david", "valores_31_12": {"2025": 900_000.0}},
            {"descricao": "FII", "proprietario": "mariana", "valores_31_12": {"2025": 100_000.0}},
        ],
        "patrimonio_por_ano": {"2025": {"total_bens": 1_050_000.0}},
    }
    titular, conjuge = build_members_from_consolidated(baseline, _DAVID)
    assert titular["ano_base"] == conjuge["ano_base"] == "2025"
    assert titular["total_bens"] == 950_000.0
