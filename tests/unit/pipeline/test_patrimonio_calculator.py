"""Testes unitários para :class:`PatrimonioCalculator` (A6d.3.3 — ADR-100).

Foca em:
- Paridade do dict de saída com ``scripts/e5_analyze.analyze_patrimonio``.
- Separação residência vs imóveis_investimento via keyword.
- Prioridade de ``investimentos_atuais`` (posições atuais) sobre IRPF fallback.
- Largest-remainder method para percentuais (soma exata = 100%).
- Tratamento de posições unattributed (``""``) → titular.
- Solo identity (sem cônjuge).
"""

from __future__ import annotations

import pytest

from pipeline.domain.services.patrimonio_calculator import PatrimonioCalculator
from pipeline.domain.services.patrimonio_types import (
    CaixaDetalhe,
    MemberIdentity,
    PatrimonioConfig,
    PatrimonioInputs,
)


@pytest.fixture
def identity() -> MemberIdentity:
    return MemberIdentity(
        titular_key="david",
        conjuge_key="mariana",
        titular_nome="David",
        conjuge_nome="Mariana",
    )


@pytest.fixture
def identity_solo() -> MemberIdentity:
    return MemberIdentity(titular_key="joao", conjuge_key="", titular_nome="João", conjuge_nome="")


@pytest.fixture
def config(identity: MemberIdentity) -> PatrimonioConfig:
    return PatrimonioConfig(members=identity, residencia_keyword="apto residência")


@pytest.fixture
def config_no_keyword(identity: MemberIdentity) -> PatrimonioConfig:
    return PatrimonioConfig(members=identity, residencia_keyword="")


# =============================================================================
# Output shape / paridade
# =============================================================================


def test_output_has_all_required_keys(config: PatrimonioConfig):
    calc = PatrimonioCalculator(config)
    result = calc.calculate(PatrimonioInputs(baseline={"members": {}}))
    required_keys = {
        "bruto",
        "dividas",
        "liquido",
        "residencia",
        "imoveis_investimento",
        "investimentos_david",
        "investimentos_mariana",
        "caixa_moeda_estrangeira",
        "caixa_detalhes",
        "investivel",
        "veiculos",
        "composicao",
        "tabela_categorias",
        "fonte_investimentos",
    }
    assert required_keys.issubset(result.keys())


def test_output_uses_dynamic_inv_keys(identity_solo: MemberIdentity):
    """key_inv_* usa identity dinâmica (``investimentos_<titular_key>``)."""
    cfg = PatrimonioConfig(members=identity_solo, residencia_keyword="")
    calc = PatrimonioCalculator(cfg)
    result = calc.calculate(PatrimonioInputs(baseline={"members": {"joao": {}}}))
    assert "investimentos_joao" in result
    # conjuge_key vazia → chave "investimentos_" ainda aparece (comportamento fiel ao legado)
    assert "investimentos_" in result


# =============================================================================
# IRPF-only flow (no current positions)
# =============================================================================


def test_irpf_only_basic_totals(config: PatrimonioConfig):
    baseline = {
        "members": {
            "david": {
                "total_bens": 1_000_000,
                "total_dividas": 100_000,
                "bens": {
                    "imoveis": [
                        {"descricao": "Apto residência nova", "valor": 500_000},
                        {"descricao": "Loja aluguel", "valor": 300_000},
                    ],
                    "veiculos": [{"descricao": "Honda", "valor": 50_000}],
                    "investimentos": [{"valor": 100_000}],
                    "contas_bancarias": [{"valor": 50_000}],
                },
            },
            "mariana": {
                "total_bens": 200_000,
                "total_dividas": 0,
                "bens": {"imoveis": [], "veiculos": [], "investimentos": []},
            },
        }
    }
    calc = PatrimonioCalculator(config)
    result = calc.calculate(PatrimonioInputs(baseline=baseline))

    assert result["fonte_investimentos"] == "irpf"
    assert result["bruto"] == 1_200_000.0  # total_bens IRPF
    assert result["dividas"] == 100_000.0
    assert result["liquido"] == 1_100_000.0
    assert result["residencia"] == 500_000.0
    assert result["imoveis_investimento"] == 300_000.0
    assert result["veiculos"] == 50_000.0
    assert result["investimentos_david"] == 150_000.0  # 100k + 50k
    # caixa residual = 1.2M - 500k - 300k - 50k - 150k = 200k
    assert result["caixa_moeda_estrangeira"] == 200_000.0


def test_irpf_only_residencia_without_keyword_match(config: PatrimonioConfig):
    """Imóvel sem matching keyword → todos vão para imoveis_investimento."""
    baseline = {
        "members": {
            "david": {
                "total_bens": 500_000,
                "bens": {"imoveis": [{"descricao": "Casa na praia", "valor": 500_000}]},
            },
            "mariana": {"total_bens": 0, "bens": {}},
        }
    }
    calc = PatrimonioCalculator(config)
    result = calc.calculate(PatrimonioInputs(baseline=baseline))
    assert result["residencia"] == 0.0
    assert result["imoveis_investimento"] == 500_000.0


def test_irpf_only_no_keyword_in_config(config_no_keyword: PatrimonioConfig):
    """Keyword vazia → todos imóveis são investimento."""
    baseline = {
        "members": {
            "david": {
                "total_bens": 500_000,
                "bens": {"imoveis": [{"descricao": "qualquer coisa", "valor": 500_000}]},
            },
            "mariana": {"total_bens": 0, "bens": {}},
        }
    }
    calc = PatrimonioCalculator(config_no_keyword)
    result = calc.calculate(PatrimonioInputs(baseline=baseline))
    assert result["residencia"] == 0.0
    assert result["imoveis_investimento"] == 500_000.0


def test_irpf_only_conjuge_imoveis_always_investimento(config: PatrimonioConfig):
    """Mesmo com keyword match, imóveis do cônjuge vão para investimento."""
    baseline = {
        "members": {
            "david": {"total_bens": 0, "bens": {}},
            "mariana": {
                "total_bens": 500_000,
                "bens": {"imoveis": [{"descricao": "Apto residência nova", "valor": 500_000}]},
            },
        }
    }
    calc = PatrimonioCalculator(config)
    result = calc.calculate(PatrimonioInputs(baseline=baseline))
    assert result["residencia"] == 0.0
    assert result["imoveis_investimento"] == 500_000.0


def test_irpf_only_caixa_floored_at_zero(config: PatrimonioConfig):
    """Caixa residual nunca negativa (soma de bens > total_bens declarado)."""
    baseline = {
        "members": {
            "david": {
                "total_bens": 100,  # intencionalmente baixo
                "bens": {
                    "imoveis": [{"descricao": "apto residência", "valor": 500}],
                    "veiculos": [{"valor": 200}],
                    "investimentos": [{"valor": 300}],
                },
            },
            "mariana": {"total_bens": 0, "bens": {}},
        }
    }
    calc = PatrimonioCalculator(config)
    result = calc.calculate(PatrimonioInputs(baseline=baseline))
    assert result["caixa_moeda_estrangeira"] == 0.0


def test_irpf_contas_bancarias_as_scalar(config: PatrimonioConfig):
    """Formato consolidated antigo usa ``contas_bancarias`` como escalar."""
    baseline = {
        "members": {
            "david": {
                "total_bens": 100_000,
                "bens": {
                    "imoveis": [],
                    "investimentos": [],
                    "contas_bancarias": 30_000,  # escalar, não lista
                },
            },
            "mariana": {"total_bens": 0, "bens": {}},
        }
    }
    calc = PatrimonioCalculator(config)
    result = calc.calculate(PatrimonioInputs(baseline=baseline))
    assert result["investimentos_david"] == 30_000.0


def test_irpf_titular_extras_summed(config: PatrimonioConfig):
    """Titular soma chaves extras: saldo_corretora, moeda_estrangeira, outros."""
    baseline = {
        "members": {
            "david": {
                "total_bens": 1000,
                "bens": {
                    "imoveis": [],
                    "investimentos": [],
                    "contas_bancarias": [],
                    "saldo_corretora": 100,
                    "moeda_estrangeira": 200,
                    "outros": 300,
                },
            },
            "mariana": {"total_bens": 0, "bens": {}},
        }
    }
    calc = PatrimonioCalculator(config)
    result = calc.calculate(PatrimonioInputs(baseline=baseline))
    assert result["investimentos_david"] == 600.0


def test_irpf_conjuge_only_outros_summed(config: PatrimonioConfig):
    """Cônjuge soma só ``outros`` — ``saldo_corretora`` e ``moeda_estrangeira`` são ignorados."""
    baseline = {
        "members": {
            "david": {"total_bens": 0, "bens": {}},
            "mariana": {
                "total_bens": 500,
                "bens": {
                    "imoveis": [],
                    "investimentos": [],
                    "contas_bancarias": [],
                    "saldo_corretora": 100,  # ignorado!
                    "moeda_estrangeira": 200,  # ignorado!
                    "outros": 300,
                },
            },
        }
    }
    calc = PatrimonioCalculator(config)
    result = calc.calculate(PatrimonioInputs(baseline=baseline))
    assert result["investimentos_mariana"] == 300.0


# =============================================================================
# Posições atuais (investimentos_atuais)
# =============================================================================


def test_current_positions_recomputes_bruto(config: PatrimonioConfig):
    """Com posições atuais, patrimonio_bruto é recomposto de fontes mistas."""
    baseline = {
        "members": {
            "david": {
                "total_bens": 999_999_999,  # valor IRPF ignorado!
                "bens": {
                    "imoveis": [{"descricao": "apto residência", "valor": 500_000}],
                    "veiculos": [{"valor": 50_000}],
                    "investimentos": [],
                },
            },
            "mariana": {"total_bens": 0, "bens": {}},
        }
    }
    inv_atuais = {
        "dados": [{"valor": 1}],  # marker de has_current_positions
        "total_por_membro": {"david": 200_000, "mariana": 100_000},
    }
    calc = PatrimonioCalculator(config)
    result = calc.calculate(
        PatrimonioInputs(
            baseline=baseline,
            investimentos_atuais=inv_atuais,
            caixa_total_brl=50_000,
            caixa_detalhes=[],
        )
    )
    assert result["fonte_investimentos"] == "posicoes_atuais"
    # 500k residência + 0 imoveis_inv + 50k veiculos + 200k titular + 100k conjuge + 50k caixa
    assert result["bruto"] == 900_000.0


def test_current_positions_unattributed_goes_to_titular(config: PatrimonioConfig):
    """Posições com membro='' vão para titular."""
    baseline = {"members": {"david": {}, "mariana": {}}}
    inv_atuais = {
        "dados": [{"valor": 1}],
        "total_por_membro": {"david": 100, "mariana": 50, "": 30},
    }
    calc = PatrimonioCalculator(config)
    result = calc.calculate(PatrimonioInputs(baseline=baseline, investimentos_atuais=inv_atuais))
    assert result["investimentos_david"] == 130.0  # 100 + 30 unattributed
    assert result["investimentos_mariana"] == 50.0


def test_current_positions_caixa_from_adapter(config: PatrimonioConfig):
    """Caixa vem pré-carregada do adapter (shell lê E3 + taxas)."""
    baseline = {"members": {"david": {}, "mariana": {}}}
    inv_atuais = {"dados": [{"valor": 1}], "total_por_membro": {}}
    caixa_detalhes = [
        CaixaDetalhe(
            conta="bofa_usd",
            moeda="USD",
            saldo_original=10_000.0,
            valor_brl=58_000.0,
            tipo="moeda_estrangeira",
        )
    ]
    calc = PatrimonioCalculator(config)
    result = calc.calculate(
        PatrimonioInputs(
            baseline=baseline,
            investimentos_atuais=inv_atuais,
            caixa_total_brl=58_000.0,
            caixa_detalhes=caixa_detalhes,
        )
    )
    assert result["caixa_moeda_estrangeira"] == 58_000.0
    assert len(result["caixa_detalhes"]) == 1
    assert result["caixa_detalhes"][0]["conta"] == "bofa_usd"
    assert result["caixa_detalhes"][0]["valor_brl"] == 58_000.0


def test_current_positions_member_without_positions_falls_back_to_irpf(
    config: PatrimonioConfig,
):
    """Quando só o titular tem posições atuais, cônjuge cai em IRPF (e vice-versa)."""
    baseline = {
        "members": {
            "david": {"total_bens": 0, "bens": {}},
            "mariana": {
                "total_bens": 250_000,
                "bens": {"investimentos": [{"valor": 250_000}]},
            },
        }
    }
    inv_atuais = {
        "dados": [{"valor": 1}],
        "total_por_membro": {"david": 300_000, "mariana": 0},
    }
    calc = PatrimonioCalculator(config)
    result = calc.calculate(PatrimonioInputs(baseline=baseline, investimentos_atuais=inv_atuais))

    assert result["investimentos_david"] == 300_000.0
    assert result["investimentos_mariana"] == 250_000.0
    assert result["fonte_investimentos"] == "posicoes_atuais+irpf"


def test_current_positions_no_fallback_when_both_have_positions(
    config: PatrimonioConfig,
):
    """Quando ambos os membros têm posições atuais, IRPF é ignorado."""
    baseline = {
        "members": {
            "david": {"bens": {"investimentos": [{"valor": 999_999}]}},
            "mariana": {"bens": {"investimentos": [{"valor": 999_999}]}},
        }
    }
    inv_atuais = {
        "dados": [{"valor": 1}],
        "total_por_membro": {"david": 100, "mariana": 50},
    }
    calc = PatrimonioCalculator(config)
    result = calc.calculate(PatrimonioInputs(baseline=baseline, investimentos_atuais=inv_atuais))

    assert result["investimentos_david"] == 100.0
    assert result["investimentos_mariana"] == 50.0
    assert result["fonte_investimentos"] == "posicoes_atuais"


def test_current_positions_empty_dados_treated_as_irpf(config: PatrimonioConfig):
    """investimentos_atuais.dados vazio → comportamento IRPF."""
    baseline = {
        "members": {
            "david": {
                "total_bens": 100,
                "bens": {"imoveis": [], "investimentos": [{"valor": 80}]},
            },
            "mariana": {"total_bens": 0, "bens": {}},
        }
    }
    inv_atuais = {"dados": [], "total_por_membro": {"david": 9999}}  # ignorado
    calc = PatrimonioCalculator(config)
    result = calc.calculate(PatrimonioInputs(baseline=baseline, investimentos_atuais=inv_atuais))
    assert result["fonte_investimentos"] == "irpf"
    assert result["investimentos_david"] == 80.0


# =============================================================================
# Composição + largest remainder method
# =============================================================================


def test_composicao_has_6_categories(config: PatrimonioConfig):
    baseline = {"members": {"david": {}, "mariana": {}}}
    calc = PatrimonioCalculator(config)
    result = calc.calculate(PatrimonioInputs(baseline=baseline))
    assert len(result["composicao"]) == 6


def test_composicao_sorted_descending(config: PatrimonioConfig):
    baseline = {
        "members": {
            "david": {
                "total_bens": 1_000_000,
                "bens": {
                    "imoveis": [{"descricao": "apto residência", "valor": 300_000}],
                    "veiculos": [{"valor": 100_000}],
                    "investimentos": [{"valor": 500_000}],
                },
            },
            "mariana": {"total_bens": 0, "bens": {}},
        }
    }
    calc = PatrimonioCalculator(config)
    result = calc.calculate(PatrimonioInputs(baseline=baseline))
    valores = [c["valor"] for c in result["composicao"]]
    assert valores == sorted(valores, reverse=True)


def test_composicao_pct_sums_to_100(config: PatrimonioConfig):
    """Largest remainder method garante pct soma exata a 100.00."""
    baseline = {
        "members": {
            "david": {
                "total_bens": 333,  # valor proposital para gerar dízima
                "bens": {
                    "imoveis": [{"descricao": "apto residência", "valor": 111}],
                    "veiculos": [{"valor": 111}],
                    "investimentos": [{"valor": 111}],
                },
            },
            "mariana": {"total_bens": 0, "bens": {}},
        }
    }
    calc = PatrimonioCalculator(config)
    result = calc.calculate(PatrimonioInputs(baseline=baseline))
    total_pct = sum(c["pct"] for c in result["composicao"])
    assert total_pct == pytest.approx(100.0, abs=0.001)


def test_composicao_zero_total_all_pcts_zero(config: PatrimonioConfig):
    baseline = {"members": {"david": {}, "mariana": {}}}
    calc = PatrimonioCalculator(config)
    result = calc.calculate(PatrimonioInputs(baseline=baseline))
    for c in result["composicao"]:
        assert c["pct"] == 0.0


def test_composicao_alias_tabela_categorias(config: PatrimonioConfig):
    """``tabela_categorias`` é alias de ``composicao`` (mesma ref)."""
    baseline = {"members": {"david": {}, "mariana": {}}}
    calc = PatrimonioCalculator(config)
    result = calc.calculate(PatrimonioInputs(baseline=baseline))
    assert result["composicao"] is result["tabela_categorias"]


# =============================================================================
# Investível
# =============================================================================


def test_investivel_excludes_residencia_and_veiculos(config: PatrimonioConfig):
    baseline = {
        "members": {
            "david": {
                "total_bens": 1_000_000,
                "bens": {
                    "imoveis": [{"descricao": "apto residência", "valor": 400_000}],
                    "veiculos": [{"valor": 100_000}],
                    "investimentos": [{"valor": 500_000}],
                },
            },
            "mariana": {"total_bens": 0, "bens": {}},
        }
    }
    calc = PatrimonioCalculator(config)
    result = calc.calculate(PatrimonioInputs(baseline=baseline))
    assert result["investivel"] == 500_000.0  # 1M - 400k residência - 100k veiculos


def test_investivel_never_negative(config: PatrimonioConfig):
    """Quando residência+veículos > bruto, investível é 0 (floor)."""
    baseline = {
        "members": {
            "david": {
                "total_bens": 100,
                "bens": {
                    "imoveis": [{"descricao": "apto residência", "valor": 500}],
                    "veiculos": [{"valor": 300}],
                },
            },
            "mariana": {"total_bens": 0, "bens": {}},
        }
    }
    calc = PatrimonioCalculator(config)
    result = calc.calculate(PatrimonioInputs(baseline=baseline))
    assert result["investivel"] == 0.0


# =============================================================================
# Liquidação (dividas aliases + solo identity)
# =============================================================================


def test_dividas_accepts_dividas_alias(config: PatrimonioConfig):
    """Aceita ``dividas`` em vez de ``total_dividas``."""
    baseline = {
        "members": {
            "david": {"total_bens": 1000, "dividas": 200, "bens": {}},
            "mariana": {"total_bens": 0, "bens": {}},
        }
    }
    calc = PatrimonioCalculator(config)
    result = calc.calculate(PatrimonioInputs(baseline=baseline))
    assert result["dividas"] == 200.0
    assert result["liquido"] == 800.0


def test_solo_identity_no_conjuge_category(identity_solo: MemberIdentity):
    cfg = PatrimonioConfig(members=identity_solo, residencia_keyword="")
    calc = PatrimonioCalculator(cfg)
    result = calc.calculate(
        PatrimonioInputs(baseline={"members": {"joao": {"total_bens": 1000, "bens": {}}}})
    )
    # Categoria do cônjuge existe mas com valor 0 + nome vazio
    cats = {c["categoria"] for c in result["composicao"]}
    assert "Investimentos " in cats  # nome vazio
    assert result["investimentos_"] == 0.0  # conjuge_key vazia
