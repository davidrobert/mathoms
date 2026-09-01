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
        compute_concentracao_imobiliaria_pct({"imoveis_alocacao": 60, "investivel_financeiro": 40})
        == 60.0
    )


def test_ancora_real_5at5():
    # Estrutura da família real (base carteira): cat_2=39,7% do bruto, financeiro=26,5%.
    # carteira = 39,7 + 26,5 = 66,2 → concentração = 39,7/66,2 = 60,0% (âncora ratificada).
    assert (
        compute_concentracao_imobiliaria_pct(
            {"imoveis_alocacao": 39.7, "investivel_financeiro": 26.5}
        )
        == 59.97
    )


def test_residencia_e_veiculos_fora_do_denominador():
    # A residência/veículos NÃO entram (só cat_2 + investível financeiro contam).
    # Mesmo cat_2/financeiro → mesma concentração, com ou sem casa/carro no dict.
    base = {"imoveis_alocacao": 60, "investivel_financeiro": 40}
    com_casa = {**base, "residencia": 500, "veiculos": 50, "bruto": 650}
    assert compute_concentracao_imobiliaria_pct(base) == compute_concentracao_imobiliaria_pct(
        com_casa
    )


def test_carteira_vazia_retorna_zero():
    assert (
        compute_concentracao_imobiliaria_pct({"imoveis_alocacao": 0, "investivel_financeiro": 0})
        == 0.0
    )
    assert compute_concentracao_imobiliaria_pct({}) == 0.0


def test_sem_imovel_retorna_zero():
    assert (
        compute_concentracao_imobiliaria_pct({"imoveis_alocacao": 0, "investivel_financeiro": 100})
        == 0.0
    )


def test_100pct_quando_so_imovel():
    assert (
        compute_concentracao_imobiliaria_pct({"imoveis_alocacao": 80, "investivel_financeiro": 0})
        == 100.0
    )


# [[ADR-420]] §D1: o que MUDA no flip é qual metade de cat_2 entra. Sem este teste, a
# troca de numerador seria invisível aqui — os fixtures acima só renomeiam a chave.
def test_cat2_completo_NAO_entra_mais_no_numerador():
    """`uso_pessoal`/`nu_proprietario` estão em cat_2 e fora da alocação."""
    from pipeline.domain.services.concentracao_imobiliaria import (
        compute_concentracao_imobiliaria_pct,
    )

    patrimonio = {
        "imoveis_alocacao": 60,
        "imoveis_investimento": 100,  # 40 fora da alocação
        "investivel_financeiro": 40,
    }

    assert (
        compute_concentracao_imobiliaria_pct(patrimonio) == 60.0
    ), "o numerador voltou a somar cat_2 completo — daria 71,43%"
