"""SSOT da concentração imobiliária — base carteira (C11-Fase2 · ADR-340).

Fórmula única consumida por ratios (E5) e pela integração real_estate (E5.N).
"""

from __future__ import annotations

from pipeline.domain.services.concentracao_imobiliaria import (
    compute_concentracao_imobiliaria_pct,
)


def test_cat2_sobre_carteira():
    # cat_2=60, financeiro=40 → carteira=100 → 60%
    assert (
        compute_concentracao_imobiliaria_pct(
            {"imoveis_investimento": 60, "investivel_financeiro": 40}
        )
        == 60.0
    )


def test_ancora_real_5at5():
    # Estrutura da família real (base carteira): cat_2=39,7% do bruto, financeiro=26,5%.
    # carteira = 39,7 + 26,5 = 66,2 → concentração = 39,7/66,2 = 60,0% (âncora ratificada).
    assert (
        compute_concentracao_imobiliaria_pct(
            {"imoveis_investimento": 39.7, "investivel_financeiro": 26.5}
        )
        == 59.97
    )


def test_residencia_e_veiculos_fora_do_denominador():
    # A residência/veículos NÃO entram (só cat_2 + investível financeiro contam).
    # Mesmo cat_2/financeiro → mesma concentração, com ou sem casa/carro no dict.
    base = {"imoveis_investimento": 60, "investivel_financeiro": 40}
    com_casa = {**base, "residencia": 500, "veiculos": 50, "bruto": 650}
    assert compute_concentracao_imobiliaria_pct(base) == compute_concentracao_imobiliaria_pct(
        com_casa
    )


def test_carteira_vazia_retorna_zero():
    assert (
        compute_concentracao_imobiliaria_pct(
            {"imoveis_investimento": 0, "investivel_financeiro": 0}
        )
        == 0.0
    )
    assert compute_concentracao_imobiliaria_pct({}) == 0.0


def test_sem_imovel_retorna_zero():
    assert (
        compute_concentracao_imobiliaria_pct(
            {"imoveis_investimento": 0, "investivel_financeiro": 100}
        )
        == 0.0
    )


def test_100pct_quando_so_imovel():
    assert (
        compute_concentracao_imobiliaria_pct(
            {"imoveis_investimento": 80, "investivel_financeiro": 0}
        )
        == 100.0
    )
