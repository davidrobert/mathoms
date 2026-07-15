"""Regressão A10.1: chaves dead-data ADR-168 (Modo USA) não voltam no seed/narrativas E5.N."""

from __future__ import annotations

from datetime import date
from typing import Any

import pytest

from pipeline.domain.services.narrativas import (
    E5NarrativasBuilder,
    NarrativasContext,
    validate_narrativas,
)

# Conjunto de chaves H deletadas do seed (Sprint A10.1).
DEAD_DATA_KEYS_SEED = {
    "fase_f1f2",
    "mariana_eua",
    "nclex_roadmap",
    "nclex_estimativa_meses",
    "investimentos_blocos",
    "aportes_destinos_detalhados",
}

# Substrings que NÃO podem aparecer no output de narrativas E5.N
# (case-insensitive). Cobertura ampla: USA/EUA, F1/F2, Green Card,
# NCLEX. Ressurgir qualquer uma sinaliza que código novo voltou a
# consumir chaves dead-data (regressão).
DEAD_DATA_SUBSTRINGS_NARRATIVAS = (
    "F1/F2",
    "F-1",
    "F-2",
    "Modo USA",
    "NCLEX",
    "Green Card",
    "Anderson University",
    "EB2-NIW",
    "tuition",
    "OPT/H-1B",
)


_FAMILY_BASE: dict[str, Any] = {
    "titular": "alice",
    "endereco": {"rua": "Rua Teste", "bairro": "Centro", "cidade": "São Paulo"},
    "pets": ["Mimi"],
    "membros": {
        "alice": {
            "papel": "titular",
            "nome_curto": "Alice",
            "nome_completo": "Alice Silva",
            "data_nascimento": "1985-03-10",
            "profissao": "Engenheira",
            "descricao_empresa": "Startup X",
            "empresas_destaque": ["BigCorp"],
            "formacao": "Computação",
            "regime": "PJ Simples",
            "carreira_inicio": 2008,
        },
        "bob": {
            "papel": "conjuge",
            "nome_curto": "Bob",
            "nome_completo": "Bob Silva",
            "data_nascimento": "1987-07-20",
            "profissao": "Enfermeiro",
            "especializacao": "UTI",
            "mestrado": "Enfermagem",
            "emprego_inicio": "2020",
            "regime": "CLT",
            "perfil_internacional": "",  # Sem mention de Green Card holder
        },
        "carol": {
            "papel": "filho",
            "nome_completo": "Carol Silva",
            "local_nascimento": "São Paulo",
            "cidadania": ["brasileira"],
        },
    },
}


def _build_minimal_metrics() -> dict[str, Any]:
    """Metrics mínimos pós-A10.1 — sem chaves f1f2/EUA/nclex."""
    return {
        "salario_conjuge": 15000,
        "if_meta": 5_000_000,
        "if_trs_pct": 4,
        "taxa_retirada_segura_pct": 4,  # ADR-191 emenda (FP-03): SWR live key
        "if_renda_passiva_meta": 16_667,
        "patrimonio_investivel": 1_500_000,
        "progresso_if": 30,
        "meta_aporte_mensal": 20_000,
        "if_retorno_real_pct": 5,
        "anos_para_if_calculo": 12,
        "idade_titular_if": 53,
        "if_ano": 2038,
        "patrimonio_bruto": 2_500_000,
        "n_imoveis": 3,
        "residencia": 800_000,
        "imoveis_investimento": 400_000,
        "investimentos_titular": 900_000,
        "investimentos_conjuge": 200_000,
        "taxa_endividamento": 8,
        "pct_investivel": 60,
        "pct_imoveis_bruto": 48,
        "score": 7.5,
        "score_label": "Saudável",
        "taxa_poupanca": 35,
        "cobertura_meses": 18,
        "receita_total": 500_000,
        "pct_receita_pj": 40,
        "pct_receita_aluguel": 15,
        "pct_receita_clt": 30,
        "pct_receita_outras": 15,
        "diversificacao": 5,
        "titular_instituicoes": "XP, BTG",
        "conjuge_instituicoes": "Nubank, Itaú",
        "receita_aluguel_anual": 60_000,
        "receita_aluguel": 50_000,
        "n_meses_periodo": 12,
        "yield_imoveis_pct": 6.5,
        "if_gap": 3_500_000,
        "if_prazo_anos": 12,
        "renda_passiva_4pct": 5_000,
        "regime_obs": "Simples Nacional",
        "das_aliquota_pct": 16,
        "das_mensal_estimado": 2_500,
        "das_anual_estimado": 30_000,
        "receita_pj_anual": 200_000,
        "contador_nome": "Fulano",
        "contador_mensal": 300,
        "contador_canal": "",
        "holding_prazo": "2027",
        "seguro_vida_minimo": 1_000_000,
        "seguro_vida_maximo": 3_000_000,
        "riscos_prioritarios": [
            {"nome": "IRS non-compliance", "prob": "média", "impacto": "alto"},
            {"nome": "FBAR missing", "prob": "alta", "impacto": "médio"},
            {"nome": "PFIC exposure", "prob": "baixa", "impacto": "alto"},
        ],
        "decisoes_prioritarias": [
            "Aporte mensal",
            "CPA expatriado",
            "Fechar holding",
            "Revisar seguros",
            "Otimizar DAS",
        ],
        "aporte_cofrinhos": 5_000,
        "aporte_ipca_plus": 8_000,
        "aporte_ivvb11": 4_000,
        "aporte_wise_usd": 3_000,
        "viagens_anuais_estimadas": 3,
        "custo_viagem_minimo": 8_000,
        "custo_viagem_maximo": 15_000,
        "receita_recorrente_mensal": 30_000,
        # Chaves cambiais ainda lidas por s6 (summary cambial — não-EUA).
        "wise_usd": 5_000,
        "bofa_usd": 3_000,
        "poupanca_cambial_actual_usd": 8_000,
        "poupanca_cambial_meta_usd": 30_000,
        "poupanca_cambial_gap_usd": 22_000,
        "aporte_cambial_mensal": 2_000,
        "meses_para_cambial": 11,
        "threshold_imovel_pct": 40,
        "aloc_instrumentos_rv": "IVVB11, BOVA11",
        "equity_alvo_min": 30,
        "equity_alvo_max": 50,
        "aloc_rf_pct": 50,
        "aloc_acoes_pct": 30,
        "aloc_instrumentos_rf": "IPCA+, LCI",
        "aloc_imoveis_pct": 10,
        "aloc_liquidez_pct": 10,
        "aloc_rebalanceamento": "trimestral",
        "despesa_mensal_media": 25_000,
        "fluxo_liquido": 150_000,
        "receita_pj": 200_000,
        "receita_clt": 150_000,
        "despesa_total": 300_000,
        "n_desp_categorias": 8,
        "despesas_nao_id": 30_000,
        "pct_despesas_nao_id": 10,
        "despesas_impostos": 50_000,
        "despesas_moradia": 40_000,
        "despesas_serv_dom": 20_000,
        "pct_renda_passiva_meta": 30,
        "yield_imoveis_potencial_pct_min": 7,
        "yield_imoveis_potencial_pct_max": 9,
        "top_asset_nome": "IPCA+ 2045",
        "top_asset_valor": 300_000,
        "top_asset_membro": "alice",
        "aportes_acum_prazo": 2_880_000,
        "cm_cenarios": ["A"],
        "cm_prazos": [18],
        "cm_aportes": [10_000],
        "cm_anos_if": [2044],
        "cm_salario_clt_brl": 15_000,
        "cm_fator_reduzido": 0.5,
    }


def test_seed_does_not_reference_dead_data_keys():
    """A10.7: seed declarativo (sem `_SKIP_SECTIONS`); chaves H não podem voltar por construção."""
    from pathlib import Path

    seed_path = (
        Path(__file__).resolve().parent.parent
        / "backend"
        / "app"
        / "scripts"
        / "seed_goals_workspace.py"
    )
    seed_source = seed_path.read_text(encoding="utf-8")
    for key in DEAD_DATA_KEYS_SEED:
        assert key not in seed_source, (
            f"Chave dead-data '{key}' aparece em seed_goals_workspace.py — "
            f"código zumbi do Modo USA voltou (ADR-168). Sprint A10.1+A10.7."
        )


def test_narrativas_output_contains_no_dead_data_substrings():
    """Output do builder de narrativas não menciona EUA/F1/F2/NCLEX/Green Card."""
    builder = E5NarrativasBuilder.from_family_config(_FAMILY_BASE)
    out = builder.build(_build_minimal_metrics(), _FAMILY_BASE, today=date(2026, 4, 20))

    # Concatena TODO o texto produzido (perfil_familia.left/right, summaries.s1..10,
    # charts[*].context+conclusion).
    all_text = ""
    pf = out.get("perfil_familia", {})
    all_text += pf.get("left", "") + " " + pf.get("right", "")
    all_text += " ".join(out.get("summaries", {}).values())
    for chart in out.get("charts", {}).values():
        if isinstance(chart, dict):
            all_text += " " + chart.get("context", "") + " " + chart.get("conclusion", "")

    for needle in DEAD_DATA_SUBSTRINGS_NARRATIVAS:
        assert needle.lower() not in all_text.lower(), (
            f"Substring dead-data '{needle}' encontrada no output das "
            f"narrativas — código zumbi do Modo USA voltou (ADR-168)."
        )


def test_validate_narrativas_does_not_require_dead_charts():
    """validate_narrativas não exige `custos_f1f2` nem `cenarios_cambiais`."""
    builder = E5NarrativasBuilder.from_family_config(_FAMILY_BASE)
    out = builder.build(_build_minimal_metrics(), _FAMILY_BASE, today=date(2026, 4, 20))

    is_valid, errors = validate_narrativas(out)
    assert is_valid, f"Narrativas devem validar pós-A10.1: {errors}"
    # Garantia explícita: validator NÃO exige charts removidos.
    error_text = " ".join(errors)
    assert "custos_f1f2" not in error_text
    assert "cenarios_cambiais" not in error_text


def test_narrativas_context_has_no_f1f2_fields():
    """NarrativasContext não tem mais campos f1f2/EUA — removidos em A10.1."""
    ctx = NarrativasContext.from_family_config(_FAMILY_BASE)
    forbidden = {"key_f1f2_titular", "key_f1f2_conjuge", "key_renda_conjuge_eua_proj"}
    for field in forbidden:
        assert not hasattr(
            ctx, field
        ), f"Campo dead-data '{field}' não pode voltar ao NarrativasContext"


@pytest.mark.parametrize(
    "metrics_key",
    [
        "f1f2_visto",
        "f1f2_universidade",
        "f1f2_green_card_via",
        "custo_fase_f1f2",
        "sobra_mensal_f1f2",
        "renda_eua_projetada_brl",
        "pct_renda_eua_vs_clt",
        "cm_renda_nclex_usd",
        "cm_renda_nclex_brl",
        "cm_renda_gc_usd",
        "cm_renda_gc_brl",
        "cm_recovery_nclex_pct",
        "cm_recovery_gc_pct",
    ],
)
def test_builder_does_not_break_when_dead_metric_keys_missing(metrics_key):
    """Builder não pode KeyError em chaves dead-data ausentes — A10.1
    removeu o consumo, então elas podem (e devem) faltar em metrics."""
    builder = E5NarrativasBuilder.from_family_config(_FAMILY_BASE)
    metrics = _build_minimal_metrics()
    metrics.pop(metrics_key, None)  # garante ausência
    # Não deve raise.
    out = builder.build(metrics, _FAMILY_BASE, today=date(2026, 4, 20))
    assert "perfil_familia" in out
    assert "summaries" in out
    assert "charts" in out
