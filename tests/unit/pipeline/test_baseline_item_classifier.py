"""Unidade do roteador ativo × passivo ([[ADR-394]] D1/D2)."""

from __future__ import annotations

import pytest

from pipeline.domain.services.baseline_item_classifier import (
    BaselineAxis,
    BaselineCatalog,
    ClassificationAuthority,
    classify_baseline_item,
)

_CATALOGO = BaselineCatalog(
    ano_base=2024,
    subtipo_por_secao_codigo={
        ("bens_direitos", "11"): "imovel",
        ("dividas_onus", "11"): "financiamento_imobiliario",
    },
)


@pytest.mark.parametrize("valor_cents", [-1, 0, 1, 20_000_000])
def test_secao_de_divida_decide_em_qualquer_sinal(valor_cents: int) -> None:
    """O sinal é veto suficiente, nunca necessário — a seção decide sozinha."""
    r = classify_baseline_item(
        codigo="11", valor_cents=valor_cents, secao="dividas_onus", categoria_hint="imovel"
    )
    assert r.eixo is BaselineAxis.PASSIVO
    assert r.autoridade is ClassificationAuthority.SECAO


def test_secao_vence_o_hint_e_a_divergencia_fica_registrada() -> None:
    r = classify_baseline_item(
        codigo="11", valor_cents=20_000_000, secao="dividas_onus", categoria_hint="imovel"
    )
    assert [w.format() for w in r.warnings] == [
        "fato (secao) roteou para passivo; categoria_hint dizia 'imovel'"
    ]


def test_catalogo_so_e_consultado_com_secao() -> None:
    """`codigo` sozinho é ambíguo: '11' rotula imóvel E dívida ([[ADR-394]] D2)."""
    sem_secao = classify_baseline_item(codigo="11", valor_cents=1, catalogo=_CATALOGO)
    assert sem_secao.subtipo is None
    com_secao = classify_baseline_item(
        codigo="11", valor_cents=1, secao="dividas_onus", catalogo=_CATALOGO
    )
    assert com_secao.subtipo == "financiamento_imobiliario"


def test_sinal_negativo_roteia_quando_nao_ha_secao() -> None:
    r = classify_baseline_item(codigo="11", valor_cents=-1, categoria_hint="imovel")
    assert r.eixo is BaselineAxis.PASSIVO
    assert r.autoridade is ClassificationAuthority.SINAL


def test_positivo_sem_secao_cai_no_hint_e_avisa() -> None:
    """O buraco que sobra do histórico — declarado, nunca silencioso."""
    r = classify_baseline_item(codigo="11", valor_cents=1, categoria_hint="imovel")
    assert r.eixo is BaselineAxis.ATIVO
    assert r.autoridade is ClassificationAuthority.HINT
    assert "categoria_hint" in r.warnings[0].format()


def test_hint_que_nomeia_divida_roteia_para_passivo_sem_sinal() -> None:
    r = classify_baseline_item(codigo="99", valor_cents=1, categoria_hint="financiamento")
    assert r.eixo is BaselineAxis.PASSIVO
    assert r.autoridade is ClassificationAuthority.HINT


def test_catalogo_marca_quando_o_ano_pedido_nao_existe() -> None:
    assert BaselineCatalog(ano_base=2024, ano_base_solicitado=2019).is_fallback
    assert not BaselineCatalog(ano_base=2024, ano_base_solicitado=2024).is_fallback


def test_yaml_real_carrega_e_indexa_pelas_duas_fichas() -> None:
    from pipeline.llm.rfb_codes import load_baseline_catalog

    catalogo = load_baseline_catalog(2024)
    assert catalogo.subtipo("dividas_onus", "11") == "financiamento_imobiliario"
    assert catalogo.subtipo("bens_direitos", "11") == "imovel"
    assert not catalogo.is_fallback


def test_ano_ausente_cai_no_mais_recente_sem_derrubar_o_run() -> None:
    """[[ADR-394]] D6 — catálogo faltando não pode abortar o E1.5c."""
    from pipeline.llm.rfb_codes import load_baseline_catalog

    catalogo = load_baseline_catalog(2019)
    assert catalogo.is_fallback
    assert catalogo.subtipo("dividas_onus", "11") == "financiamento_imobiliario"
