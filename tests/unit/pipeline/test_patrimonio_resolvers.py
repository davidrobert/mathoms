"""Testes unitários para ``pipeline.domain.services.patrimonio_resolvers``.

Cobertura:
- :func:`resolve_members` dispatcher para 4 formatos de baseline.
- :func:`build_members_from_declarations` (formato E1.5 declarations).
- :func:`build_members_from_consolidated` (formato v1.5 + E1.5 v2).

Todos os testes são puros — zero I/O, zero config global.
"""

from __future__ import annotations

import pytest

from pipeline.domain.services.patrimonio_resolvers import (
    _classify_bens_by_grupo,
    _extract_membro_key,
    _infer_ano_base,
    _is_conjuge_exclusive,
    _resolve_ano_ref,
    _resolve_item_valor,
    build_members_from_consolidated,
    build_members_from_declarations,
    resolve_members,
)
from pipeline.domain.services.patrimonio_types import MemberIdentity


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
    """Titular sem cônjuge."""
    return MemberIdentity(titular_key="joao", conjuge_key="", titular_nome="João", conjuge_nome="")


# =============================================================================
# resolve_members — dispatcher
# =============================================================================


def test_resolve_members_dict_format(identity: MemberIdentity):
    baseline = {
        "members": {
            "david": {"total_bens": 1000},
            "mariana": {"total_bens": 500},
        }
    }
    titular, conjuge = resolve_members(baseline, identity)
    assert titular == {"total_bens": 1000}
    assert conjuge == {"total_bens": 500}


def test_resolve_members_membros_key_alias(identity: MemberIdentity):
    """Baseline usa ``membros`` em vez de ``members``."""
    baseline = {
        "membros": {"david": {"x": 1}, "mariana": {"y": 2}},
    }
    titular, conjuge = resolve_members(baseline, identity)
    assert titular == {"x": 1}
    assert conjuge == {"y": 2}


def test_resolve_members_list_of_dicts(identity: MemberIdentity):
    baseline = {
        "membros": [
            {"nome": "David Silva", "total_bens": 100},
            {"nome": "Mariana Souza", "total_bens": 200},
        ]
    }
    titular, conjuge = resolve_members(baseline, identity)
    assert titular == {"nome": "David Silva", "total_bens": 100}
    assert conjuge == {"nome": "Mariana Souza", "total_bens": 200}


def test_resolve_members_solo_identity_no_conjuge_returned(
    identity_solo: MemberIdentity,
):
    baseline = {"members": {"joao": {"total_bens": 1}, "mariana": {"x": 2}}}
    titular, conjuge = resolve_members(baseline, identity_solo)
    assert titular == {"total_bens": 1}
    assert conjuge == {}


def test_resolve_members_list_of_strings_with_declarations(
    identity: MemberIdentity,
):
    """Membros como lista de strings + declarations → declarations path."""
    baseline = {
        "membros": ["david", "mariana"],
        "declarations": [
            {
                "membro": "david",
                "ano_base": 2024,
                "total_bens": 500000,
                "bens_direitos": [{"grupo": "01", "situacao_atual": 300000, "descricao": "Apt"}],
            }
        ],
    }
    titular, conjuge = resolve_members(baseline, identity)
    assert titular["total_bens"] == 500000
    assert len(titular["bens"]["imoveis"]) == 1
    assert conjuge == {}


def test_resolve_members_list_of_strings_with_consolidated(
    identity: MemberIdentity,
):
    """Membros como lista + imoveis_consolidados → consolidated path."""
    baseline = {
        "membros": ["david", "mariana"],
        "imoveis_consolidados": [{"proprietario": "david", "valor": 300000}],
        "patrimonio_por_ano": {"2024": {"total_bens": 300000}},
    }
    titular, _ = resolve_members(baseline, identity)
    assert titular["total_bens"] == 300000


def test_resolve_members_empty_members_fallback_to_consolidated(
    identity: MemberIdentity,
):
    """Sem 'members' e sem 'membros' → cai no consolidated."""
    baseline = {"imoveis_consolidados": []}
    titular, conjuge = resolve_members(baseline, identity)
    # Consolidated com listas vazias → totais zero
    assert titular["total_bens"] == 0
    assert conjuge["total_bens"] == 0


# =============================================================================
# _classify_bens_by_grupo
# =============================================================================


def test_classify_bens_grupo_01_imoveis():
    bens = [{"grupo": "01", "situacao_atual": 500000, "descricao": "Apt SP"}]
    out = _classify_bens_by_grupo(bens)
    assert len(out["imoveis"]) == 1
    assert out["imoveis"][0]["valor_31_12_ano_base"] == 500000


def test_classify_bens_grupo_02_veiculos():
    bens = [{"grupo": "02", "situacao_atual": 50000, "descricao": "Carro"}]
    out = _classify_bens_by_grupo(bens)
    assert len(out["veiculos"]) == 1


def test_classify_bens_grupos_investimentos():
    """G03/G04/G07/G99 → investimentos."""
    bens = [
        {"grupo": "03", "situacao_atual": 1000, "descricao": "Ações"},
        {"grupo": "04", "situacao_atual": 2000, "descricao": "CDB"},
        {"grupo": "07", "situacao_atual": 3000, "descricao": "Fundo"},
        {"grupo": "99", "situacao_atual": 4000, "descricao": "Outro"},
    ]
    out = _classify_bens_by_grupo(bens)
    assert len(out["investimentos"]) == 4
    total = sum(b["valor_31_12_ano_base"] for b in out["investimentos"])
    assert total == 10000


def test_classify_bens_grupo_06_contas():
    bens = [{"grupo": "06", "situacao_atual": 5000, "descricao": "Conta"}]
    out = _classify_bens_by_grupo(bens)
    assert len(out["contas_bancarias"]) == 1


def test_classify_bens_grupo_prefix_g_stripped():
    """'G01' normaliza para '01'."""
    bens = [{"grupo": "G01", "situacao_atual": 100, "descricao": "x"}]
    out = _classify_bens_by_grupo(bens)
    assert len(out["imoveis"]) == 1


def test_classify_bens_grupo_numeric_int():
    """Inteiro 1 normaliza para '01'."""
    bens = [{"grupo": 1, "situacao_atual": 100, "descricao": "x"}]
    out = _classify_bens_by_grupo(bens)
    assert len(out["imoveis"]) == 1


def test_classify_bens_grupo_single_digit_str():
    """'1' normaliza para '01'."""
    bens = [{"grupo": "2", "situacao_atual": 100, "descricao": "x"}]
    out = _classify_bens_by_grupo(bens)
    assert len(out["veiculos"]) == 1


def test_classify_bens_unknown_grupo_goes_investimentos():
    bens = [{"grupo": "77", "situacao_atual": 100, "descricao": "x"}]
    out = _classify_bens_by_grupo(bens)
    assert len(out["investimentos"]) == 1


def test_classify_bens_fallback_valor_31_12_atual():
    """Se ``situacao_atual`` não existir, usa ``valor_31_12_atual``."""
    bens = [{"grupo": "01", "valor_31_12_atual": 999, "descricao": "x"}]
    out = _classify_bens_by_grupo(bens)
    assert out["imoveis"][0]["valor_31_12_ano_base"] == 999


def test_classify_bens_empty_list_returns_empty_cats():
    out = _classify_bens_by_grupo([])
    assert out == {
        "imoveis": [],
        "veiculos": [],
        "investimentos": [],
        "contas_bancarias": [],
    }


# =============================================================================
# _extract_membro_key / _infer_ano_base
# =============================================================================


def test_extract_membro_key_from_membro_field(identity: MemberIdentity):
    assert _extract_membro_key({"membro": "David Silva"}, identity) == "david"
    assert _extract_membro_key({"membro": "Mariana Souza"}, identity) == "mariana"


def test_extract_membro_key_from_declarante_nome(identity: MemberIdentity):
    """IRPF format: declarante.nome em vez de membro."""
    decl = {"declarante": {"nome": "David Silva"}}
    assert _extract_membro_key(decl, identity) == "david"


def test_extract_membro_key_none_when_no_match(identity: MemberIdentity):
    assert _extract_membro_key({"membro": "Terceiro"}, identity) is None


def test_extract_membro_key_prefers_membro_over_declarante(
    identity: MemberIdentity,
):
    """``membro`` tem prioridade sobre ``declarante.nome``."""
    decl = {"membro": "david", "declarante": {"nome": "mariana"}}
    assert _extract_membro_key(decl, identity) == "david"


def test_infer_ano_base_direct():
    assert _infer_ano_base({"ano_base": 2023}) == 2023


def test_infer_ano_base_from_source_file():
    assert _infer_ano_base({"source_file": "decl_2024.pdf"}) == 2024


def test_infer_ano_base_from_nested_filename():
    """Apenas o último segmento do path é inspecionado (paridade com legado)."""
    assert _infer_ano_base({"source_file": "/tmp/irpf/2022/decl_2024.pdf"}) == 2024


def test_infer_ano_base_nested_path_without_year_in_filename_returns_zero():
    """Path nested com ano só no diretório (não no filename) → 0."""
    assert _infer_ano_base({"source_file": "/tmp/irpf/2022/decl.pdf"}) == 0


def test_infer_ano_base_zero_when_missing():
    assert _infer_ano_base({}) == 0


# =============================================================================
# build_members_from_declarations
# =============================================================================


def test_declarations_empty_returns_empty_tuple(identity: MemberIdentity):
    assert build_members_from_declarations({}, identity) == ({}, {})


def test_declarations_single_titular(identity: MemberIdentity):
    baseline = {
        "declarations": [
            {
                "membro": "david",
                "ano_base": 2024,
                "total_bens": 1_000_000,
                "bens_direitos": [
                    {"grupo": "01", "situacao_atual": 500_000, "descricao": "Apt"},
                    {"grupo": "04", "situacao_atual": 200_000, "descricao": "CDB"},
                ],
            }
        ]
    }
    titular, conjuge = build_members_from_declarations(baseline, identity)
    assert titular["total_bens"] == 1_000_000
    assert len(titular["bens"]["imoveis"]) == 1
    assert len(titular["bens"]["investimentos"]) == 1
    assert conjuge == {}


def test_declarations_selects_most_recent_ano_base(identity: MemberIdentity):
    baseline = {
        "declarations": [
            {
                "membro": "david",
                "ano_base": 2022,
                "total_bens": 100,
                "bens_direitos": [],
            },
            {
                "membro": "david",
                "ano_base": 2024,
                "total_bens": 999,
                "bens_direitos": [],
            },
        ]
    }
    titular, _ = build_members_from_declarations(baseline, identity)
    assert titular["total_bens"] == 999


def test_declarations_both_members(identity: MemberIdentity):
    baseline = {
        "declarations": [
            {
                "membro": "david",
                "ano_base": 2024,
                "total_bens": 500,
                "bens_direitos": [],
            },
            {
                "membro": "mariana",
                "ano_base": 2024,
                "total_bens": 300,
                "bens_direitos": [],
            },
        ]
    }
    titular, conjuge = build_members_from_declarations(baseline, identity)
    assert titular["total_bens"] == 500
    assert conjuge["total_bens"] == 300


def test_declarations_dividas_attribution(identity: MemberIdentity):
    baseline = {
        "declarations": [
            {
                "membro": "david",
                "ano_base": 2024,
                "total_bens": 1000,
                "bens_direitos": [],
            }
        ],
        "dividas": [
            {"proprietario": "david", "saldo_31_12": 100},
            {"proprietario": "david", "saldo_31_12": 50},
            {"proprietario": "mariana", "saldo_31_12": 200},
        ],
    }
    titular, _ = build_members_from_declarations(baseline, identity)
    assert titular["total_dividas"] == 150


def test_declarations_synthetic_total_when_decl_total_zero(identity: MemberIdentity):
    """Se total_bens declarado = 0, usa synthetic (soma dos bens)."""
    baseline = {
        "declarations": [
            {
                "membro": "david",
                "ano_base": 2024,
                "total_bens": 0,
                "bens_direitos": [
                    {"grupo": "01", "situacao_atual": 500_000, "descricao": "Apt"},
                ],
            }
        ]
    }
    titular, _ = build_members_from_declarations(baseline, identity)
    assert titular["total_bens"] == 500_000


def test_declarations_solo_identity_no_conjuge(identity_solo: MemberIdentity):
    """Titular solo (sem conjuge_key) → conjuge sempre {}."""
    baseline = {
        "declarations": [
            {"membro": "joao", "ano_base": 2024, "total_bens": 100, "bens_direitos": []}
        ]
    }
    titular, conjuge = build_members_from_declarations(baseline, identity_solo)
    assert titular["total_bens"] == 100
    assert conjuge == {}


# =============================================================================
# _resolve_ano_ref
# =============================================================================


def test_resolve_ano_ref_patrimonio_por_ano():
    baseline = {
        "patrimonio_por_ano": {
            "2022": {"total_bens": 100, "total_dividas": 10},
            "2024": {"total_bens": 500, "total_dividas": 50},
        }
    }
    ano, bens, div = _resolve_ano_ref(baseline)
    assert ano == "2024"
    assert bens == 500
    assert div == 50


def test_resolve_ano_ref_e15_v2_resumo():
    baseline = {
        "resumo_patrimonial": {
            "31_12_2024": {"total": 1_000_000},
            "variacao_2023_2024": {"pct": 10},
        },
        "cálculo_patrimonio_liquido": {"2024": {"ativo_total": 1_000_000, "passivo_total": 50_000}},
    }
    ano, bens, div = _resolve_ano_ref(baseline)
    assert ano == "2024"
    assert bens == 1_000_000
    assert div == 50_000


def test_resolve_ano_ref_e15_v2_calculo_fallback_when_resumo_total_zero():
    """Se resumo tem a chave do ano mas total=0, cai para calculo.ativo_total."""
    baseline = {
        "resumo_patrimonial": {
            "31_12_2024": {"total": 0},  # zero → fallback
            "variacao_2023_2024": {},  # filtrada (starts with variacao_)
        },
        "cálculo_patrimonio_liquido": {"2024": {"ativo_total": 999, "passivo_total": 11}},
    }
    ano, bens, div = _resolve_ano_ref(baseline)
    assert ano == "2024"
    assert bens == 999
    assert div == 11


def test_resolve_ano_ref_calculo_sem_cedilha_aceito():
    """Aceita ``calculo_patrimonio_liquido`` sem cedilha."""
    baseline = {
        "resumo_patrimonial": {"31_12_2024": {}},
        "calculo_patrimonio_liquido": {"2024": {"ativo_total": 42, "passivo_total": 7}},
    }
    ano, bens, div = _resolve_ano_ref(baseline)
    assert ano == "2024"
    assert bens == 42
    assert div == 7


# =============================================================================
# _resolve_item_valor
# =============================================================================


def test_resolve_item_valor_prefers_valores_31_12_ano():
    item = {"valores_31_12": {"2024": 1000}}
    assert _resolve_item_valor(item, "2024") == 1000


def test_resolve_item_valor_accepts_prefixed_key():
    """``valores_31_12.31_12_2024`` também funciona."""
    item = {"valores_31_12": {"31_12_2024": 500}}
    assert _resolve_item_valor(item, "2024") == 500


def test_resolve_item_valor_fallback_valor_YYYY():
    item = {"valor_2024": 300}
    assert _resolve_item_valor(item, "2024") == 300


def test_resolve_item_valor_fallback_valor():
    item = {"valor": 77}
    assert _resolve_item_valor(item, "2024") == 77


def test_resolve_item_valor_zero_when_missing():
    assert _resolve_item_valor({}, "2024") == 0.0


# =============================================================================
# _is_conjuge_exclusive
# =============================================================================


def test_conjuge_exclusive_string_positive(identity: MemberIdentity):
    assert _is_conjuge_exclusive({"proprietario": "Mariana Silva"}, identity) is True


def test_conjuge_exclusive_string_shared_with_titular(identity: MemberIdentity):
    assert _is_conjuge_exclusive({"proprietario": "David & Mariana"}, identity) is False


def test_conjuge_exclusive_list_positive(identity: MemberIdentity):
    assert _is_conjuge_exclusive({"proprietarios": ["Mariana"]}, identity) is True


def test_conjuge_exclusive_list_shared(identity: MemberIdentity):
    assert _is_conjuge_exclusive({"proprietarios": ["David", "Mariana"]}, identity) is False


def test_conjuge_exclusive_false_for_solo_identity(identity_solo: MemberIdentity):
    """Solo identity nunca marca como exclusivo do cônjuge."""
    assert _is_conjuge_exclusive({"proprietario": "mariana"}, identity_solo) is False


def test_conjuge_exclusive_false_when_titular(identity: MemberIdentity):
    assert _is_conjuge_exclusive({"proprietario": "David"}, identity) is False


# =============================================================================
# build_members_from_consolidated
# =============================================================================


def test_consolidated_original_format_basic(identity: MemberIdentity):
    baseline = {
        "patrimonio_por_ano": {"2024": {"total_bens": 500000, "total_dividas": 0}},
        "imoveis_consolidados": [
            {
                "proprietario": "david",
                "descricao": "Apt Centro",
                "valor_2024": 300000,
            },
            {
                "proprietario": "mariana",
                "descricao": "Casa Litoral",
                "valor_2024": 200000,
            },
        ],
    }
    titular, conjuge = build_members_from_consolidated(baseline, identity)
    assert len(titular["bens"]["imoveis"]) == 1
    assert titular["bens"]["imoveis"][0]["descricao"] == "Apt Centro"
    assert len(conjuge["bens"]["imoveis"]) == 1
    assert titular["total_bens"] == 300000
    assert conjuge["total_bens"] == 200000


def test_consolidated_e15_v2_aliased_keys(identity: MemberIdentity):
    """E1.5 v2 usa ``bens_imoveis_consolidados`` + ``investimentos_financeiros_consolidados``."""
    baseline = {
        "resumo_patrimonial": {"31_12_2024": {"total": 100000}},
        "cálculo_patrimonio_liquido": {"2024": {"ativo_total": 100000, "passivo_total": 0}},
        "bens_imoveis_consolidados": [
            {"proprietario": "david", "endereco": "Rua X", "valor_2024": 100000},
        ],
        "investimentos_financeiros_consolidados": {},
    }
    titular, _ = build_members_from_consolidated(baseline, identity)
    assert len(titular["bens"]["imoveis"]) == 1
    assert titular["bens"]["imoveis"][0]["endereco"] == "Rua X"


def test_consolidated_dados_completos_imovel_as_desc(identity: MemberIdentity):
    """Quando ``descricao`` vazia, descrição vem de ``dados_completos.imovel``."""
    baseline = {
        "patrimonio_por_ano": {"2024": {}},
        "imoveis_consolidados": [
            {
                "proprietario": "david",
                "descricao": "",
                "dados_completos": {"imovel": "Apartamento 3 quartos"},
                "valor_2024": 1,
            }
        ],
    }
    titular, _ = build_members_from_consolidated(baseline, identity)
    assert titular["bens"]["imoveis"][0]["descricao"] == "Apartamento 3 quartos"


def test_consolidated_investments_as_dict_e15v2(identity: MemberIdentity):
    """Formato E1.5 v2: ``investimentos_financeiros_consolidados`` como dict."""
    baseline = {
        "patrimonio_por_ano": {"2024": {}},
        "investimentos_financeiros_consolidados": {
            "david_2024": {
                "renda_fixa": 1000,
                "acoes": 2000,
                "total": 3000,  # ignorado
            },
            "mariana_2024": {
                "cripto": 500,
            },
        },
    }
    titular, conjuge = build_members_from_consolidated(baseline, identity)
    assert len(titular["bens"]["investimentos"]) == 2
    categorias_titular = {i["tipo"] for i in titular["bens"]["investimentos"]}
    assert categorias_titular == {"renda_fixa", "acoes"}
    assert titular["total_bens"] == 3000
    assert conjuge["total_bens"] == 500


def test_consolidated_investments_dict_skips_zero_values(identity: MemberIdentity):
    baseline = {
        "patrimonio_por_ano": {"2024": {}},
        "investimentos_financeiros_consolidados": {"david_2024": {"acoes": 0, "renda_fixa": 100}},
    }
    titular, _ = build_members_from_consolidated(baseline, identity)
    assert len(titular["bens"]["investimentos"]) == 1
    assert titular["bens"]["investimentos"][0]["tipo"] == "renda_fixa"


def test_consolidated_investments_as_list_original(identity: MemberIdentity):
    baseline = {
        "patrimonio_por_ano": {"2024": {}},
        "investimentos_consolidados": [
            {"proprietario": "david", "descricao": "CDB", "valor": 500},
        ],
    }
    titular, _ = build_members_from_consolidated(baseline, identity)
    assert len(titular["bens"]["investimentos"]) == 1
    assert titular["bens"]["investimentos"][0]["descricao"] == "CDB"


def test_consolidated_veiculos(identity: MemberIdentity):
    baseline = {
        "patrimonio_por_ano": {"2024": {}},
        "veiculos_consolidados": [
            {"proprietario": "david", "descricao": "Honda Civic", "valor_2024": 80000},
            {"proprietario": "mariana", "descricao": "Toyota Corolla", "valor_2024": 70000},
        ],
    }
    titular, conjuge = build_members_from_consolidated(baseline, identity)
    assert len(titular["bens"]["veiculos"]) == 1
    assert len(conjuge["bens"]["veiculos"]) == 1


def test_consolidated_dividas_aliased_key(identity: MemberIdentity):
    """Aceita ``dividas`` ou ``dividas_consolidadas``."""
    baseline = {
        "patrimonio_por_ano": {"2024": {}},
        "dividas_consolidadas": [
            {"proprietario": "david", "saldo_31_12": {"2024": 100}},
            {"proprietario": "mariana", "saldo_31_12": {"2024": 50}},
        ],
    }
    titular, conjuge = build_members_from_consolidated(baseline, identity)
    assert titular["total_dividas"] == 100
    assert conjuge["total_dividas"] == 50


def test_consolidated_shared_divida_goes_to_titular(identity: MemberIdentity):
    """Dívida sem proprietário exclusivo do cônjuge → titular."""
    baseline = {
        "patrimonio_por_ano": {"2024": {}},
        "dividas": [
            {"proprietario": "conjunto david mariana", "saldo_31_12": {"2024": 200}},
        ],
    }
    titular, conjuge = build_members_from_consolidated(baseline, identity)
    assert titular["total_dividas"] == 200
    assert conjuge["total_dividas"] == 0


def test_consolidated_diff_allocated_to_titular(identity: MemberIdentity):
    """Diferença entre synthetic total e total_bens do resumo vai para titular."""
    baseline = {
        "patrimonio_por_ano": {"2024": {"total_bens": 1000, "total_dividas": 0}},
        "imoveis_consolidados": [
            {"proprietario": "david", "descricao": "Apt", "valor_2024": 500},
        ],
        # synthetic=500, resumo=1000 → diff=500 alocado ao titular
    }
    titular, conjuge = build_members_from_consolidated(baseline, identity)
    assert titular["total_bens"] == 1000


def test_consolidated_solo_identity_conjuge_empty(identity_solo: MemberIdentity):
    baseline = {
        "patrimonio_por_ano": {"2024": {}},
        "imoveis_consolidados": [{"proprietario": "joao", "descricao": "Apt", "valor_2024": 100}],
    }
    titular, conjuge = build_members_from_consolidated(baseline, identity_solo)
    assert titular["total_bens"] == 100
    assert conjuge == {}
