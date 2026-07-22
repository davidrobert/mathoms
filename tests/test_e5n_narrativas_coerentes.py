"""A37.l8 — narrativas coerentes com os dados (FIN-03 + FIN-05 + FIN-08).

Regressão dos três comportamentos corrigidos (co-design financial-planner
2026-07-22; decisões de domínio colhidas na revisão do sprint 2026-07-20):

- FIN-03: s4 usa aluguel recorrente atual (mediana da última sequência
  contígua > 0, cap 6 meses) + âncora anual do IRPF (``passive_income``)
  + sinal de vacância (≥2 zeros no fim da série). Nunca anualiza média
  que cruza vacância; s4 não emite yield % (único yield da S4 é o
  ``RealEstateYieldCard``).
- FIN-05: chart ``alocacao_atual_vs_alvo`` consome a taxonomia v2
  (``goals.alocacao_alvo.derived.comparaveis``, mesma base do card) e
  aposenta as chaves do rollup v1 (``aloc_rf_pct`` e irmãs).
- FIN-08: chart ``projecao_3cenarios`` usa linguagem probabilística com
  ``if_monte_carlo`` ("cenário central <ano>; ~X% de chance até <idade>");
  nunca "será atingida" determinístico.
"""

from __future__ import annotations

from typing import Any

import pytest

from pipeline.domain.services.narrativas import (
    ChartsNarrator,
    NarrativasContext,
    SummariesNarrator,
    fmt_currency,
)

_FAMILY: dict[str, Any] = {
    "titular": "alice",
    "endereco": {"rua": "Rua Teste"},
    "membros": {
        "alice": {"papel": "titular", "nome_curto": "Alice", "data_nascimento": "1985-03-10"},
        "bob": {"papel": "conjuge", "nome_curto": "Bob", "data_nascimento": "1987-07-20"},
    },
}


# Métricas mínimas para SummariesNarrator + ChartsNarrator (dict puro);
# s1..s10 precisam das chaves indexadas para narrate não explodir em KeyError.
_METRICS_MINIMAS: dict[str, Any] = {
    "patrimonio_bruto": 2_500_000,
    "patrimonio_investivel": 1_500_000,
    "pct_investivel": 60,
    "pct_imoveis_bruto": 48,
    "residencia": 800_000,
    "imoveis_investimento": 400_000,
    "taxa_endividamento": 8,
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
    "conjuge_instituicoes": "Nubank",
    "investimentos_titular": 900_000,
    "investimentos_conjuge": 200_000,
    "n_imoveis": 3,
    "receita_aluguel": 120_000,
    "n_meses_periodo": 40,
    "receita_recorrente_mensal": 30_000,
    "despesa_mensal_media": 25_000,
    "wise_usd": 5_000,
    "bofa_usd": 3_000,
    "poupanca_cambial_actual_usd": 8_000,
    "poupanca_cambial_meta_usd": 30_000,
    "poupanca_cambial_gap_usd": 22_000,
    "aporte_cambial_mensal": 2_000,
    "meses_para_cambial": 11,
    "if_meta": 5_000_000,
    "if_ano": 2038,
    "if_gap": 3_500_000,
    "if_prazo_anos": 12,
    "if_trs_pct": 5,
    "taxa_retirada_segura_pct": 4,
    "if_renda_passiva_meta": 16_667,
    "if_retorno_real_pct": 5,
    "meta_aporte_mensal": 20_000,
    "renda_passiva_4pct": 5_000,
    "pct_renda_passiva_meta": 30,
    "idade_titular_if": 53,
    "anos_para_if_calculo": 12,
    "aportes_acum_prazo": 2_880_000,
    "regime_obs": "Simples Nacional",
    "das_aliquota_pct": 16,
    "das_mensal_estimado": 2_500,
    "das_anual_estimado": 30_000,
    "receita_pj_anual": 200_000,
    "contador_nome": "",
    "contador_mensal": 0,
    "contador_canal": "",
    "holding_prazo": "",
    "tributario_section": None,
    "seguro_vida_minimo": 1_000_000,
    "seguro_vida_maximo": 3_000_000,
    "aporte_distribuicao": {},
    "viagens_anuais_estimadas": 0,
    "custo_viagem_minimo": 0,
    "custo_viagem_maximo": 0,
    "threshold_imovel_pct": 40,
    "despesa_total": 300_000,
    "n_desp_categorias": 8,
    "despesas_nao_id": 30_000,
    "pct_despesas_nao_id": 10,
    "despesas_impostos": 50_000,
    "despesas_moradia": 40_000,
    "despesas_serv_dom": 20_000,
    "fluxo_liquido": 150_000,
    "receita_pj": 200_000,
    "receita_clt": 150_000,
    "top_asset_nome": "IPCA+ 2045",
    "top_asset_valor": 300_000,
    "top_asset_membro": "alice",
    "wise_fiscal_flags": [],
    "cm_prazos": [],
    "cm_aportes": [],
    "cm_anos_if": [],
    "cm_salario_clt_brl": 0,
    "cm_fator_reduzido": 0.66,
    "aloc_rebalanceamento": "por_aporte",
    # A37.l8 — novos campos canônicos (defaults vazios)
    "aluguel_mensal_recorrente": 0.0,
    "aluguel_janela_meses": 0,
    "aluguel_meses_sem_entrada": 0,
    "aluguel_anual_irpf": 0.0,
    "aluguel_irpf_ano_ref": None,
    "aloc_derived": {},
    "mc_p50_ano_if": None,
    "mc_prob_if_ate_idade_meta": None,
    "mc_idade_meta": None,
}


def _metrics_base() -> dict[str, Any]:
    return dict(_METRICS_MINIMAS)


def _ctx() -> NarrativasContext:
    return NarrativasContext.from_family_config(_FAMILY)


def _s4(metrics: dict[str, Any]) -> str:
    return SummariesNarrator(_ctx()).narrate(metrics, _FAMILY, [], [])["s4"]


def _charts(metrics: dict[str, Any]) -> dict[str, Any]:
    return ChartsNarrator(_ctx()).narrate(metrics, _FAMILY, [], [])


def _e5_data_minimal() -> dict[str, Any]:
    return {
        "patrimonio": {},
        "goals": {},
        "fluxo_caixa": {},
        "ratios": {},
        "score": {},
        "reserva_emergencia": {},
    }


@pytest.fixture()
def e5n(tmp_path, monkeypatch):
    """Módulo legado inicializado num workspace vazio (padrão de test_narrativas_empty_field_guards)."""
    import scripts.generate_narratives as e5n_mod

    e5n_mod._init_config(tmp_path)
    monkeypatch.setattr(e5n_mod, "_load_taxas", lambda: {})
    yield e5n_mod
    e5n_mod._init_config(e5n_mod._DEFAULT_BASE_DIR)


# ----------------------------------------------------------------------
# FIN-03 — métricas: aluguel recorrente atual + vacância + âncora IRPF
# ----------------------------------------------------------------------


def _e5_com_serie_aluguel(serie: list[float]) -> dict[str, Any]:
    data = _e5_data_minimal()
    data["fluxo_caixa"] = {
        "receita_despesa_mensal_detalhado": {
            "labels": [f"26/{i:02d}" for i in range(1, len(serie) + 1)],
            "receita_datasets": [
                {"label": "Aluguéis", "data": serie},
                {"label": "Outras Receitas", "data": [100.0] * len(serie)},
            ],
        },
    }
    return data


def test_metrics_aluguel_recorrente_janela_estavel(e5n):
    """Mediana dos últimos ≤6 meses da sequência contígua > 0 — não a média histórica."""
    serie = [3000.0] * 34 + [3500.0] * 6
    metrics = e5n.load_metrics_from_e5(_e5_com_serie_aluguel(serie))
    assert metrics["aluguel_mensal_recorrente"] == 3500.0
    assert metrics["aluguel_janela_meses"] == 6
    assert metrics["aluguel_meses_sem_entrada"] == 0


def test_metrics_aluguel_vacancia_recente(e5n):
    """Zeros no fim da série viram contagem de meses sem entrada (sinal de vacância)."""
    serie = [3000.0] * 37 + [0.0, 0.0, 0.0]
    metrics = e5n.load_metrics_from_e5(_e5_com_serie_aluguel(serie))
    assert metrics["aluguel_mensal_recorrente"] == 3000.0
    assert metrics["aluguel_meses_sem_entrada"] == 3


def test_metrics_aluguel_vacancia_intermediaria_nao_contamina(e5n):
    """Vacância no meio + retomada: janela usa só a sequência mais recente."""
    serie = [2000.0] * 20 + [0.0] * 4 + [4000.0] * 3
    metrics = e5n.load_metrics_from_e5(_e5_com_serie_aluguel(serie))
    assert metrics["aluguel_mensal_recorrente"] == 4000.0
    assert metrics["aluguel_janela_meses"] == 3
    assert metrics["aluguel_meses_sem_entrada"] == 0


def test_metrics_sem_aluguel(e5n):
    metrics = e5n.load_metrics_from_e5(_e5_data_minimal())
    assert metrics["aluguel_mensal_recorrente"] == 0.0
    assert metrics["aluguel_janela_meses"] == 0
    assert metrics["aluguel_meses_sem_entrada"] == 0


def test_metrics_ancora_irpf_reconcilia_com_passive_income(e5n):
    """Âncora anual = passive_income.alugueis (mesmo número, não um terceiro valor)."""
    data = _e5_data_minimal()
    data["passive_income"] = {
        "status": "ok",
        "renda_passiva_por_fonte_brl": {"alugueis": 48_000.0, "dividendos": 10_000.0},
        "ano_referencia_irpf": 2024,
    }
    metrics = e5n.load_metrics_from_e5(data)
    assert metrics["aluguel_anual_irpf"] == 48_000.0
    assert metrics["aluguel_irpf_ano_ref"] == 2024


def test_metrics_ancora_irpf_ausente_quando_status_nao_ok(e5n):
    data = _e5_data_minimal()
    data["passive_income"] = {
        "status": "sem_irpf",
        "renda_passiva_por_fonte_brl": {"alugueis": 48_000.0},
        "ano_referencia_irpf": 2024,
    }
    metrics = e5n.load_metrics_from_e5(data)
    assert metrics["aluguel_anual_irpf"] == 0.0
    assert metrics["aluguel_irpf_ano_ref"] is None


def test_metrics_nao_anualiza_media_historica(e5n):
    """As chaves do comportamento antigo (média 40m anualizada + yield diluído) morrem."""
    serie = [3000.0] * 38 + [0.0, 0.0]
    metrics = e5n.load_metrics_from_e5(_e5_com_serie_aluguel(serie))
    assert "receita_aluguel_anual" not in metrics
    assert "yield_imoveis_pct" not in metrics


# ----------------------------------------------------------------------
# FIN-03 — s4: prosa sem yield %, com vacância explícita e âncora IRPF
# ----------------------------------------------------------------------


def test_s4_aluguel_recorrente_sem_yield():
    m = _metrics_base() | {
        "aluguel_mensal_recorrente": 3500.0,
        "aluguel_janela_meses": 6,
        "aluguel_anual_irpf": 42_000.0,
        "aluguel_irpf_ano_ref": 2024,
    }
    s4 = _s4(m)
    assert fmt_currency(3500.0) + "/mês" in s4
    assert "recorrente" in s4.lower()
    assert "IRPF 2024" in s4
    assert fmt_currency(42_000.0) + "/ano" in s4
    assert "yield" not in s4.lower()
    assert "%" not in s4


def test_s4_vacancia_explicita_sem_anualizacao():
    m = _metrics_base() | {
        "aluguel_mensal_recorrente": 3000.0,
        "aluguel_janela_meses": 6,
        "aluguel_meses_sem_entrada": 3,
        "aluguel_anual_irpf": 33_500.0,
        "aluguel_irpf_ano_ref": 2024,
    }
    s4 = _s4(m)
    assert "sem entrada de aluguel nos últimos 3 meses" in s4
    assert "vacância" in s4.lower()
    # Sem projeção anual do recorrente quando há vacância (só a âncora IRPF tem /ano).
    assert fmt_currency(3000.0 * 12) + "/ano" not in s4
    assert fmt_currency(33_500.0) + "/ano" in s4


def test_s4_um_zero_final_nao_sinaliza_vacancia():
    """1 zero no fim pode ser corte de extrato — sinal exige ≥2 (co-design)."""
    m = _metrics_base() | {
        "aluguel_mensal_recorrente": 3000.0,
        "aluguel_janela_meses": 6,
        "aluguel_meses_sem_entrada": 1,
    }
    s4 = _s4(m)
    assert "vacância" not in s4.lower()
    assert "recorrente" in s4.lower()


def test_s4_sem_aluguel_estado_honesto():
    m = _metrics_base() | {"receita_aluguel": 0}
    s4 = _s4(m)
    assert "Sem renda de aluguel" in s4
    assert "R$ 0,00/mês" not in s4


def test_s4_total_periodo_quando_serie_indisponivel():
    """Payload sem série mensal mas com receita_aluguel > 0: cita o total, sem anualizar."""
    m = _metrics_base()  # receita_aluguel=120k, recorrente=0
    s4 = _s4(m)
    assert fmt_currency(120_000) in s4
    assert "/ano" not in s4


# ----------------------------------------------------------------------
# FIN-05 — alocação: narrativa cita a taxonomia v2 (mesma base do card)
# ----------------------------------------------------------------------

_DERIVED_V2: dict[str, Any] = {
    "comparaveis": [
        {
            "classe": "renda_fixa",
            "valor_brl": 460_000.0,
            "atual_pct": 46.0,
            "alvo_pct": 62.0,
            "desvio_pp": -16.0,
            "severity": "rebalancear",
        },
        {
            "classe": "acoes_br",
            "valor_brl": 180_000.0,
            "atual_pct": 18.0,
            "alvo_pct": 15.0,
            "desvio_pp": 3.0,
            "severity": "atencao",
        },
        {
            "classe": "acoes_int",
            "valor_brl": 120_000.0,
            "atual_pct": 12.0,
            "alvo_pct": 15.0,
            "desvio_pp": -3.0,
            "severity": "atencao",
        },
        {
            "classe": "fiis",
            "valor_brl": 60_000.0,
            "atual_pct": 6.0,
            "alvo_pct": 8.0,
            "desvio_pp": -2.0,
            "severity": "alinhado",
        },
        {
            "classe": "fora_alvo",
            "valor_brl": 180_000.0,
            "atual_pct": 18.0,
            "alvo_pct": 0.0,
            "desvio_pp": 18.0,
            "severity": "rebalancear",
        },
    ],
    "desvio_max_pct": 18.0,
    "next_aporte_classe": "renda_fixa",
    "carteira_liquida_brl": 1_000_000.0,
    "caixa": {
        "valor_brl": 50_000.0,
        "atual_pct_patrimonio": 3.4,
        "alvo_pct": 5.0,
        "excesso_pp": None,
        "sinal_excesso": False,
    },
    "imoveis_fisicos_brl": 400_000.0,
    "has_alvo": True,
    "rf_comparacao": "agregada",
    "alvo_renormalizado_defensivo": False,
}


def test_alocacao_narrativa_cita_classes_v2():
    charts = _charts(_metrics_base() | {"aloc_derived": _DERIVED_V2})
    aloc = charts["alocacao_atual_vs_alvo"]
    texto = aloc["context"] + " " + aloc["conclusion"]
    # Labels em paridade com o card (alocacaoCardParts.tsx).
    for label in ("Renda Fixa", "Ações BR", "Ações Int.", "FIIs", "Fora do alvo"):
        assert label in texto, label
    # Percentuais atual→alvo da tabela (mesma base do card).
    assert "46%" in aloc["conclusion"] and "62%" in aloc["conclusion"]
    assert "18 pp" in aloc["conclusion"]
    # Base declarada: carteira líquida; caixa e imóveis fora.
    assert "carteira líquida" in aloc["context"].lower()
    # Rollup v1 aposentado: sem "Imóveis/REITs" nem "Liquidez/USD" (labels v1).
    assert "Imóveis/REITs" not in texto
    assert "Liquidez/USD" not in texto


def test_alocacao_next_aporte_label_mapeado():
    derived = dict(_DERIVED_V2, next_aporte_classe="acoes_int")
    charts = _charts(_metrics_base() | {"aloc_derived": derived})
    conclusion = charts["alocacao_atual_vs_alvo"]["conclusion"]
    assert "Ações Int." in conclusion
    assert "acoes_int" not in conclusion


def test_alocacao_sem_alvo_nao_inventa_numeros():
    charts = _charts(_metrics_base() | {"aloc_derived": {}})
    aloc = charts["alocacao_atual_vs_alvo"]
    texto = (aloc["context"] + " " + aloc["conclusion"]).lower()
    assert "não definida" in texto or "sem alvo" in texto
    assert aloc["context"] and aloc["conclusion"]
    assert "%" not in aloc["conclusion"]


def test_metrics_aloc_derived_wiring_e_v1_aposentado(e5n):
    """`aloc_derived` vem do payload E5 (goals.alocacao_alvo.derived) — mesma base do card."""
    data = _e5_data_minimal()
    data["goals"] = {"alocacao_alvo": {"rf_pos_pct": 40, "derived": _DERIVED_V2}}
    metrics = e5n.load_metrics_from_e5(data)
    assert metrics["aloc_derived"] == _DERIVED_V2
    for chave_v1 in ("aloc_rf_pct", "aloc_acoes_pct", "aloc_imoveis_pct", "aloc_liquidez_pct"):
        assert chave_v1 not in metrics, chave_v1


# ----------------------------------------------------------------------
# FIN-08 — projeção IF probabilística (if_monte_carlo)
# ----------------------------------------------------------------------


def test_projecao_probabilistica_com_monte_carlo():
    m = _metrics_base() | {
        "mc_p50_ano_if": 2039,
        "mc_prob_if_ate_idade_meta": 0.41,
        "mc_idade_meta": 65,
    }
    conclusion = _charts(m)["projecao_3cenarios"]["conclusion"]
    assert "2039" in conclusion
    assert "41%" in conclusion
    assert "65" in conclusion
    assert "será atingida" not in conclusion


def test_projecao_fallback_deterministico_sem_promessa():
    conclusion = _charts(_metrics_base())["projecao_3cenarios"]["conclusion"]
    assert "2038" in conclusion
    assert "será atingida" not in conclusion
    assert "será" not in conclusion


@pytest.mark.parametrize(
    ("prob", "esperado"),
    [(0.004, "<1%"), (0.995, ">99%"), (0.5, "50%")],
)
def test_projecao_probabilidade_guards(prob: float, esperado: str):
    m = _metrics_base() | {
        "mc_p50_ano_if": 2039,
        "mc_prob_if_ate_idade_meta": prob,
        "mc_idade_meta": 65,
    }
    conclusion = _charts(m)["projecao_3cenarios"]["conclusion"]
    assert esperado in conclusion


def test_metrics_monte_carlo_wiring(e5n):
    data = _e5_data_minimal()
    data["if_monte_carlo"] = {
        "p50_ano_if": 2040,
        "prob_if_ate_idade_meta": 0.4123,
        "idade_meta_usada": 65,
    }
    metrics = e5n.load_metrics_from_e5(data)
    assert metrics["mc_p50_ano_if"] == 2040
    assert metrics["mc_prob_if_ate_idade_meta"] == 0.4123
    assert metrics["mc_idade_meta"] == 65
