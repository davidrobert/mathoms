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


def _e5_protecao(apolice_numero: str = "51.824.917 236") -> dict:
    """Seção protecao_patrimonial sintética no shape do schema (ApoliceResumo)."""
    return {
        "protecao_patrimonial": {
            "apolices_vigentes": [
                {
                    "apolice_numero": apolice_numero,
                    "seguradora": "portoseguro",
                    "vigencia_inicio": "2026-01-01",
                    "vigencia_fim": "2026-12-31",
                    "premio_total_brl": "1234.56",
                    "bens_count": 2,
                }
            ],
            "gap_qualitativo": {"vida": True, "saude": False},
        }
    }


def test_sanitize_redige_apolice_numero_por_chave():
    """ADR-341 D6 (A37.l1 PR-2a): identificador estrutural redigido por chave declarada."""
    out = sanitize_e5_for_parecer(_e5_protecao(), ())
    apolice = out["protecao_patrimonial"]["apolices_vigentes"][0]
    assert apolice["apolice_numero"] == "[REDIGIDO]"
    # irmãos da mesma apólice ficam intactos (redação é cirúrgica, por chave)
    assert apolice["seguradora"] == "portoseguro"
    assert apolice["premio_total_brl"] == "1234.56"
    assert apolice["bens_count"] == 2
    assert out["protecao_patrimonial"]["gap_qualitativo"] == {"vida": True, "saude": False}


def test_sanitize_redige_apolice_numero_aninhado():
    """Chave declarada redige em qualquer profundidade (ex.: congenere_anterior)."""
    e5 = _e5_protecao()
    e5["protecao_patrimonial"]["apolices_vigentes"][0]["congenere_anterior"] = {
        "seguradora": "tokiomarine",
        "apolice_numero": "PR-2043615-A",
    }
    out = sanitize_e5_for_parecer(e5, ())
    congenere = out["protecao_patrimonial"]["apolices_vigentes"][0]["congenere_anterior"]
    assert congenere == {"seguradora": "tokiomarine", "apolice_numero": "[REDIGIDO]"}


def test_sanitize_apolice_numero_none_permanece_none():
    """Ausência continua ausência — redigir None fabricaria presença de dado."""
    out = sanitize_e5_for_parecer(_e5_protecao(apolice_numero=None), ())
    assert out["protecao_patrimonial"]["apolices_vigentes"][0]["apolice_numero"] is None


def test_sanitize_tool_path_nao_devolve_apolice_numero():
    """Regressão no caminho das tools: get_e5_section sobre e5 sanitizado (mesmo
    objeto que o orchestrator injeta no PlannerDrillDown) não devolve o número."""
    import json

    from pipeline.llm.tools.planner_drill_down import PlannerDrillDown

    seeded = _e5_protecao()
    clean = sanitize_e5_for_parecer(seeded, ())
    drill = PlannerDrillDown(
        e5_data=clean, section_whitelist=frozenset({"protecao_patrimonial"}), format_hints={}
    )
    result = drill.get_e5_section("protecao_patrimonial")
    assert result.found
    payload = json.dumps(result.to_llm_payload(), ensure_ascii=False, default=str)
    assert "51.824.917 236" not in payload
    assert "[REDIGIDO]" in payload


def test_sanitize_guard_over_redacao_prosa_cep_valores():
    """Guard ADR-341: redação por chave NÃO toca prosa monetária, CEP nem valores
    numéricos legítimos (a alternativa regex-de-dígitos rejeitada faria isso)."""
    e5 = {
        "narrativas": {
            "resumo": "Prêmio anual de R$ 1.234,56 concentra 2.043.615 pontos no programa."
        },
        "patrimonio": {
            "imoveis": [{"endereco_cep": "01310-100", "valor": 850000.0}],
            "liquido": 1234567.89,
        },
        "fluxo_caixa": {"referencia": "2026-06", "saldo_medio": "15560.00"},
    }
    out = sanitize_e5_for_parecer(e5, ())
    assert out == e5  # nada além das chaves declaradas é redigido
