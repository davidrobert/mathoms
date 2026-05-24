"""Golden test — A6d.3.2 (decomposição E5.N em domain services).

Complementa ``test_e5n_e7_main_with_store_parity.py`` cobrindo a
arquitetura introduzida em A6d.3.2:

- :class:`E5NarrativasBuilder` orquestra 3 narradores de seção
- :class:`NarrativasContext` concentra as 10+ keys derivadas por membro
- Format helpers + validator vivem em
  ``pipeline.domain.services.narrativas.format_helpers``

Cobertura:
1. **Structural golden** — builder retorna ``{perfil_familia, summaries,
   charts}`` com contagem e chaves corretas (via fixture mínima).
2. **Dynamic keys** — mudar nomes de membros em ``family_members.json``
   propaga em ``charts`` (key dinâmica do bloco de cenários do cônjuge)
   e ``summaries`` (mentions ``ctx.titular_nome``/``ctx.conjuge_nome``).
3. **Delegação legado** — ``scripts.e5n_narrativas.build_narrativas``
   delega ao builder (paridade bit-a-bit).

Tolerância: estrutural + exato, sem tolerâncias numéricas (narrativas
são texto, não metric).
"""

from __future__ import annotations

from datetime import date
from typing import Any

import pytest

from pipeline.domain.services.narrativas import (
    ChartsNarrator,
    E5NarrativasBuilder,
    NarrativasContext,
    PerfilFamiliaNarrator,
    SummariesNarrator,
    fmt_currency,
    fmt_num,
    fmt_percent,
    fmt_usd,
    validate_narrativas,
)

# ----------------------------------------------------------------------
# Fixtures mínimas (só o que o builder precisa — M + FAMILY)
# ----------------------------------------------------------------------

_FAMILY_BASE: dict[str, Any] = {
    "titular": "alice",
    "endereco": {"rua": "Rua Teste", "bairro": "Centro", "cidade": "São Paulo"},
    "pets": ["Mimi", "Luna"],
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
            "empregador_curto": "Hospital Y",
            "regime": "CLT",
            "perfil_internacional": "Green Card holder",
        },
        "carol": {
            "papel": "filho",
            "nome_completo": "Carol Silva",
            "local_nascimento": "São Paulo",
            "cidadania": ["brasileira", "americana"],
        },
    },
}


def _build_metrics() -> dict[str, Any]:
    """Metrics mínimos cobrindo todas as chaves usadas pelos 3 narradores."""
    return {
        # perfil_familia
        "salario_bob": 15000,
        "f1f2_visto": "F-1",
        "f1f2_universidade": "NYU",
        "f1f2_green_card_via": "OPT/H-1B",
        "f1f2_estrategia_alice": "Alice mantém PJ remoto",
        "f1f2_estrategia_bob": "Bob aplica NCLEX",
        "custo_fase_f1f2": 25000,
        "sobra_mensal_f1f2": 5000,
        "if_meta": 5_000_000,
        "if_trs_pct": 4,
        "if_renda_passiva_meta": 16_667,
        "patrimonio_investivel": 1_500_000,
        "progresso_if": 30,
        "meta_aporte_mensal": 20_000,
        "if_retorno_real_pct": 5,
        "anos_para_if_calculo": 12,
        "idade_alice_if": 53,
        "if_ano": 2038,
        "patrimonio_bruto": 2_500_000,
        "n_imoveis": 3,
        "residencia": 800_000,
        "imoveis_investimento": 400_000,
        "investimentos_alice": 900_000,
        "investimentos_bob": 200_000,
        "taxa_endividamento": 8,
        # summaries (keys extras)
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
        "alice_instituicoes": "XP, BTG",
        "bob_instituicoes": "Nubank, Itaú",
        "receita_aluguel_anual": 60_000,
        "receita_aluguel": 50_000,
        "n_meses_periodo": 12,
        "yield_imoveis_pct": 6.5,
        "wise_usd": 5_000,
        "bofa_usd": 3_000,
        "poupanca_cambial_actual_usd": 8_000,
        "poupanca_cambial_meta_usd": 30_000,
        "poupanca_cambial_gap_usd": 22_000,
        "aporte_cambial_mensal": 2_000,
        "meses_para_cambial": 11,
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
        # ADR-236 §D4: bundle["tributario"] expandido (fixture happy-path Simples-III).
        "tributario_section": {
            "regime": "simples",
            "regime_label": "Simples Nacional — Anexo III",
            "cascata": {
                "regime": "simples",
                "regime_label": "Simples Nacional — Anexo III",
                "regime_nao_suportado": False,
                "motivo_nao_suportado": None,
                "receita_bruta": 200_000.0,
                "tributos_federais": 12_000.0,
                "iss_total": 0.0,
                "lucro_contabil_pj": 178_000.0,
                "pro_labore_bruto": 18_000.0,
                "inss_patronal": 0.0,
                "inss_empregado": 1_980.0,
                "irrf_pro_labore": 0.0,
                "lucros_distribuidos": 60_000.0,
                "renda_pf_tributavel_total": 38_000.0,
                "carga_total_pct": 0.06,
                "pgbl_base_anual": 38_000.0,
                "pgbl_limite_anual": 4_560.0,
                "pgbl_aplicavel": True,
                "pgbl_motivo_inaplicavel": None,
                "fator_r_pct": 0.30,
                "fator_r_faixa": "anexo_iii",
                "fator_r_break_even_mensal": 0.0,
                "triggers": [],
            },
            "contador_nome": "Fulano",
            "holding_prazo_meses": 12,
            "_source": "db:business_profile_json + e3/e4/e1.6 derived",
        },
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
        # charts (extras)
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
        "cm_cenarios": ["A", "B", "C"],
        "cm_prazos": [18, 10, 8],
        "cm_aportes": [10_000, 20_000, 25_000],
        "cm_anos_if": [2044, 2036, 2034],
        "cm_salario_clt_brl": 15_000,
        "cm_renda_nclex_usd": 6_000,
        "cm_renda_gc_usd": 10_000,
        "cm_renda_nclex_brl": 32_000,
        "cm_renda_gc_brl": 52_000,
        "cm_recovery_nclex_pct": 110,
        "cm_recovery_gc_pct": 180,
        "cm_fator_reduzido": 0.5,
        "cambio_usd_brl": 5.2,
        "f1f2_crescimento_salarial": 8,
        "renda_bob_eua_projetada": 8_000,
        "renda_eua_projetada_brl": 41_600,
    }


# ----------------------------------------------------------------------
# 1. Structural golden
# ----------------------------------------------------------------------


def test_builder_returns_three_top_level_sections():
    builder = E5NarrativasBuilder.from_family_config(_FAMILY_BASE)
    metrics = _build_metrics()
    out = builder.build(metrics, _FAMILY_BASE, today=date(2026, 4, 20))
    assert set(out.keys()) == {"perfil_familia", "summaries", "charts"}


def test_builder_summaries_has_s1_through_s10():
    builder = E5NarrativasBuilder.from_family_config(_FAMILY_BASE)
    out = builder.build(_build_metrics(), _FAMILY_BASE, today=date(2026, 4, 20))
    assert list(out["summaries"].keys()) == [f"s{i}" for i in range(1, 11)]
    for key, text in out["summaries"].items():
        assert isinstance(text, str) and text, f"{key} vazio"


def test_builder_perfil_familia_has_left_and_right():
    builder = E5NarrativasBuilder.from_family_config(_FAMILY_BASE)
    out = builder.build(_build_metrics(), _FAMILY_BASE, today=date(2026, 4, 20))
    pf = out["perfil_familia"]
    assert set(pf.keys()) == {"left", "right"}
    assert "<p>" in pf["left"] and "<p>" in pf["right"]
    # Não pode conter tags proibidas pelo validator.
    for side in ("left", "right"):
        assert "<table" not in pf[side].lower()
        assert "<ul" not in pf[side].lower()


def test_builder_charts_has_all_18_required_keys():
    """ADR-168 cleanup (Sprint A10.1): charts custos_f1f2 e cenarios_cambiais
    removidos. A17 L3 P5 adiciona `wise_fiscal_flags` (opt-in: context vazio
    quando workspace não tem informe Wise — não exige conteúdo)."""
    builder = E5NarrativasBuilder.from_family_config(_FAMILY_BASE)
    ctx = NarrativasContext.from_family_config(_FAMILY_BASE)
    out = builder.build(_build_metrics(), _FAMILY_BASE, today=date(2026, 4, 20))
    expected = {
        "score_gauge",
        "patrimonio_doughnut",
        "alocacao_atual",
        "alocacao_alvo",
        "fluxo_mensal",
        "receita_bar",
        "receita_despesa_mensal",
        "despesas_doughnut",
        "projecao_3cenarios",
        "waterfall_if",
        "renda_passiva",
        "top15_ativos",
        "impostos_pj",
        "cenarios_conjuge",  # ADR-176: chave universal estável (era <conjuge>_cenarios)
        "viagens",
        "bubble_riscos",
        "top5_decisoes",
        "wise_fiscal_flags",  # A17 L3 P5 — opt-in (vazio quando sem informe Wise)
    }
    assert set(out["charts"].keys()) == expected
    # wise_fiscal_flags é opt-in — context/conclusion vazios quando sem flags.
    optional_empty = {"wise_fiscal_flags"}
    for k, v in out["charts"].items():
        assert "context" in v and "conclusion" in v, f"{k}: chaves ausentes"
        if k in optional_empty:
            continue
        assert v["context"], f"{k}: context vazio"
        assert v["conclusion"], f"{k}: conclusion vazio"


def test_builder_output_passes_validator():
    builder = E5NarrativasBuilder.from_family_config(_FAMILY_BASE)
    out = builder.build(_build_metrics(), _FAMILY_BASE, today=date(2026, 4, 20))
    # ADR-176: validate_narrativas usa default "cenarios_conjuge" — não há
    # mais chave dinâmica para repassar.
    is_valid, errors = validate_narrativas(out)
    assert is_valid, f"Validação falhou: {errors}"


def test_top15_ativos_conclusion_omits_maior_ativo_when_data_missing():
    # Regressão: bug visível no relatório quando _find_top_asset cai no fallback
    # (E4 ausente) — narrador renderizava "(R$ 0,00 de ) é o maior ativo individual".
    builder = E5NarrativasBuilder.from_family_config(_FAMILY_BASE)
    metrics = _build_metrics() | {
        "top_asset_nome": "",
        "top_asset_valor": 0,
        "top_asset_membro": "",
    }
    out = builder.build(metrics, _FAMILY_BASE, today=date(2026, 4, 20))
    conclusion = out["charts"]["top15_ativos"]["conclusion"]
    assert "R$ 0,00" not in conclusion
    assert "é o maior ativo individual" not in conclusion
    assert "diversificação" in conclusion


def test_top15_ativos_conclusion_uses_data_when_present():
    builder = E5NarrativasBuilder.from_family_config(_FAMILY_BASE)
    out = builder.build(_build_metrics(), _FAMILY_BASE, today=date(2026, 4, 20))
    conclusion = out["charts"]["top15_ativos"]["conclusion"]
    assert "IPCA+ 2045" in conclusion
    assert "Alice" in conclusion
    assert "é o maior ativo individual" in conclusion


# ----------------------------------------------------------------------
# 2. Dynamic keys — troca de nomes propaga
# ----------------------------------------------------------------------


def test_context_dynamic_keys_change_with_family():
    family_alt = {
        "titular": "xavier",
        "membros": {
            "xavier": {"papel": "titular", "nome_curto": "Xavier"},
            "yolanda": {"papel": "conjuge", "nome_curto": "Yolanda"},
        },
    }
    ctx = NarrativasContext.from_family_config(family_alt)
    assert ctx.titular_key == "xavier"
    assert ctx.conjuge_key == "yolanda"
    assert ctx.titular_nome == "Xavier"
    assert ctx.conjuge_nome == "Yolanda"
    assert ctx.key_inv_titular == "investimentos_xavier"
    assert ctx.key_inv_conjuge == "investimentos_yolanda"
    # ADR-176: chave de cenários é universal, não derivada do cônjuge.
    assert ctx.key_cenarios_conjuge == "cenarios_conjuge"


def test_builder_charts_key_cenarios_uses_universal_key():
    """ADR-176: chart de cenários cônjuge usa chave universal ``cenarios_conjuge`` — regressão-bloqueada (frontend lê essa key fixa)."""
    builder = E5NarrativasBuilder.from_family_config(_FAMILY_BASE)
    out = builder.build(_build_metrics(), _FAMILY_BASE, today=date(2026, 4, 20))
    assert "cenarios_conjuge" in out["charts"]
    assert out["charts"]["cenarios_conjuge"]["context"]
    # Garantia explícita: nenhuma chave derivada de membro permanece.
    assert "bob_cenarios" not in out["charts"]


# ----------------------------------------------------------------------
# 3. Delegação — legado chama o builder (bit-a-bit)
# ----------------------------------------------------------------------


def test_legacy_build_narrativas_delegates_to_builder(monkeypatch, tmp_path):
    """``scripts.e5n_narrativas.build_narrativas`` deve produzir output
    bit-a-bit idêntico ao builder direto.
    """
    import scripts.e5n_narrativas as e5n
    import scripts.pipeline_common as _pc

    # Re-inicializa para workspace limpo (evita globals de outra sessão).
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "family_members.json").write_text(
        __import__("json").dumps(_FAMILY_BASE), encoding="utf-8"
    )
    (tmp_path / "config" / "categorization.json").write_text("{}", encoding="utf-8")
    (tmp_path / "config" / "pipeline.json").write_text("{}", encoding="utf-8")

    _pc._init_config(tmp_path)
    try:
        e5n._init_config(tmp_path)
        metrics = _build_metrics()
        e5n.METRICS.clear()
        e5n.METRICS.update(metrics)

        via_legacy = e5n.build_narrativas()

        ctx = NarrativasContext.from_family_config(e5n.FAMILY)
        builder = E5NarrativasBuilder(ctx)
        via_builder = builder.build(metrics, e5n.FAMILY)

        # Narrativas não envolvem datas dinâmicas no summary — a única
        # diferença possível seria a data de hoje no perfil_familia
        # (cálculo de idade). Ambos os caminhos usam date.today(), então
        # devem coincidir dentro da mesma execução.
        assert via_legacy == via_builder
    finally:
        e5n._init_config(e5n._DEFAULT_BASE_DIR)


# ----------------------------------------------------------------------
# 4. Format helpers — smoke (já cobertos por test_e5n_formatting.py)
# ----------------------------------------------------------------------


def test_format_helpers_backwards_compat():
    """Aliases em ``scripts.e5n_narrativas`` continuam funcionando."""
    import scripts.e5n_narrativas as e5n

    assert e5n.fmt_currency(1_500_000) == "R$ 1,5M"
    assert e5n.fmt_percent(35) == "35%"
    assert e5n.fmt_num(7.5) == "7,5"
    assert e5n.fmt_usd(5_000) == "US$ 5k"
    # E também via domain module.
    assert fmt_currency(1_500_000) == e5n.fmt_currency(1_500_000)
    assert fmt_percent(35) == e5n.fmt_percent(35)
    assert fmt_num(7.5) == e5n.fmt_num(7.5)
    assert fmt_usd(5_000) == e5n.fmt_usd(5_000)


# ----------------------------------------------------------------------
# 5. Sub-narradores acessíveis via public API
# ----------------------------------------------------------------------


def test_sub_narrators_are_exported():
    """Cada narrador é acessível individualmente (composição flexível)."""
    ctx = NarrativasContext.from_family_config(_FAMILY_BASE)

    pf = PerfilFamiliaNarrator(ctx).narrate(_build_metrics(), _FAMILY_BASE, today=date(2026, 4, 20))
    assert "left" in pf and "right" in pf

    sm = SummariesNarrator(ctx).narrate(
        _build_metrics(),
        _FAMILY_BASE,
        ["risco1", "risco2", "risco3"],
        ["d1", "d2", "d3", "d4"],
    )
    assert set(sm.keys()) == {f"s{i}" for i in range(1, 11)}

    ch = ChartsNarrator(ctx).narrate(
        _build_metrics(),
        _FAMILY_BASE,
        [
            {"nome": "r1", "prob": "a", "impacto": "a"},
            {"nome": "r2", "prob": "a", "impacto": "a"},
            {"nome": "r3", "prob": "a", "impacto": "a"},
        ],
        ["d1", "d2", "d3", "d4"],
    )
    assert "score_gauge" in ch and ctx.key_cenarios_conjuge in ch
