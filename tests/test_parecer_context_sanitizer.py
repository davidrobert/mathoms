"""CTO-03 (ADR-332): sanitizer de PII do contexto do parecer — nome→papel + CPF/CNPJ.

Nomes sintéticos (Fulano/Beltrano/Sicrano); zero PII real.
"""

from __future__ import annotations

from backend.app.services.parecer_context_sanitizer import (
    build_name_role_pairs,
    sanitize_e5_for_parecer,
)

_FAMILY = {
    "titular": "fulano",
    "membros": {
        "fulano": {"nome_curto": "Fulano", "papel": "titular"},
        "beltrano": {"nome_curto": "Beltrano", "papel": "conjuge"},
        "sicrano": {"nome_curto": "Sicrano", "papel": "filho"},
    },
}


def test_build_name_role_pairs_papeis():
    pairs = dict(build_name_role_pairs(_FAMILY))
    assert pairs == {"Fulano": "Titular", "Beltrano": "Cônjuge", "Sicrano": "Dependente"}


def test_build_name_role_pairs_ordinal_multi_dependente():
    fam = {
        "titular": "fulano",
        "membros": {
            "fulano": {"nome_curto": "Fulano", "papel": "titular"},
            "sicrano": {"nome_curto": "Sicrano", "papel": "filho"},
            "zeca": {"nome_curto": "Zeca", "papel": "filho"},
        },
    }
    pairs = dict(build_name_role_pairs(fam))
    # ordinal estável por ordem de key (sicrano < zeca)
    assert pairs["Sicrano"] == "Dependente 1"
    assert pairs["Zeca"] == "Dependente 2"


def test_build_name_role_pairs_sem_membros():
    assert build_name_role_pairs({}) == ()
    assert build_name_role_pairs(None) == ()


def test_sanitize_membro_categoria_label_para_papel():
    pairs = build_name_role_pairs(_FAMILY)
    e5 = {
        "investimentos": {"top_ativos": [{"membro": "Fulano", "valor": 100000.0}]},
        "patrimonio": {"composicao": [{"categoria": "Investimentos Beltrano", "valor": 50000.0}]},
        "fluxo_caixa": {"receita_datasets": [{"label": "CLT Fulano"}]},
    }
    out = sanitize_e5_for_parecer(e5, pairs)
    assert out["investimentos"]["top_ativos"][0]["membro"] == "Titular"
    assert out["investimentos"]["top_ativos"][0]["valor"] == 100000.0  # ADR-090: número intacto
    assert out["patrimonio"]["composicao"][0]["categoria"] == "Investimentos Cônjuge"
    assert out["fluxo_caixa"]["receita_datasets"][0]["label"] == "CLT Titular"


def test_sanitize_scrubs_dict_keys():
    pairs = build_name_role_pairs(_FAMILY)
    e5 = {
        "fluxo_caixa": {"por_fonte_detalhado": {"PIX Fulano": 3000.0, "Salario Beltrano": 8000.0}}
    }
    out = sanitize_e5_for_parecer(e5, pairs)
    fontes = out["fluxo_caixa"]["por_fonte_detalhado"]
    assert set(fontes) == {"PIX Titular", "Salario Cônjuge"}
    assert fontes["PIX Titular"] == 3000.0


def test_sanitize_nome_curto_2_chars_nao_vaza():
    # Finding da revisão adversarial: nome <3 chars vazava. _MIN_NAME_LEN=2 pega "Zé".
    fam = {"titular": "ze", "membros": {"ze": {"nome_curto": "Zé", "papel": "titular"}}}
    pairs = build_name_role_pairs(fam)
    e5 = {"investimentos": {"top_ativos": [{"membro": "Zé", "valor": 1.0}]}}
    out = sanitize_e5_for_parecer(e5, pairs)
    assert out["investimentos"]["top_ativos"][0]["membro"] == "Titular"


def test_sanitize_redige_cpf_cnpj():
    e5 = {"nota": "titular CPF 123.456.789-00 e empresa 12.345.678/0001-90"}
    out = sanitize_e5_for_parecer(e5, ())
    assert "123.456.789-00" not in out["nota"]
    assert "12.345.678/0001-90" not in out["nota"]
    assert "[id-redigido]" in out["nota"]


def test_sanitize_nao_muta_original():
    pairs = build_name_role_pairs(_FAMILY)
    e5 = {"investimentos": {"top_ativos": [{"membro": "Fulano"}]}}
    sanitize_e5_for_parecer(e5, pairs)
    assert e5["investimentos"]["top_ativos"][0]["membro"] == "Fulano"  # cópia, não in-place
