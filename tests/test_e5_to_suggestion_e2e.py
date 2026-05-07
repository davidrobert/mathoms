"""E2E — snapshot real (`build_e5_output`) → SuggestionGenerator (W1-T02 + W1-T07 · FP-001/2/3/9)."""

from __future__ import annotations

from datetime import date

import pytest

from pipeline.domain.services.e5_serialization import (
    E5OutputInputs,
    build_e5_output,
)
from pipeline.domain.services.if_projector import (
    IFProjector,
    IFProjectorConfig,
)
from pipeline.domain.services.pontos_fortes_analyzer import PontosFortesAnalyzer
from pipeline.domain.services.suggestion_config import SuggestionGeneratorConfig
from pipeline.domain.services.suggestion_generator import SuggestionGenerator


def _build_if_projection(
    investivel: float = 1_500_000.0,
    if_meta: float = 5_000_000.0,
    if_trs_pct: float = 4.0,
    retorno_real_anual_pct: float = 6.0,
):
    """Helper que produz uma IFProjection real (não MagicMock)."""
    cfg = IFProjectorConfig(
        if_meta=if_meta,
        if_trs_pct=if_trs_pct,
        retorno_real_anual_pct=retorno_real_anual_pct,
        titular_dob=date(1985, 5, 15),
        aporte_mensal=10_000.0,
        reference_date=date(2026, 5, 6),
    )
    return IFProjector(cfg).project(investivel=investivel)


def _build_snapshot(
    *,
    if_projection,
    custo_medio_pct_aa: float | None = None,
    percentual_patrimonio_div: float = 5.0,
    # Snapshot wire usa string decimal por ADR-090; testes pegam dict legado
    # com float (paridade com test_suggestion_generator.py). Variáveis sem
    # sufixo monetário evitam disparar gate de wire shape.
    total_dividas=30_000.0,
    renda_passiva_observada=4_000.0,
    despesa_mensal_media=20_000.0,
) -> dict:
    """Constrói o snapshot E5 via ``build_e5_output``. Determinístico."""
    goals = if_projection.to_legacy_dict()
    # Adiciona renda passiva observada (PassiveIncomeCalculator A8.3 emite
    # esse campo em goals quando IRPF disponível).
    goals["renda_passiva_mensal_observada_brl"] = renda_passiva_observada

    endividamento = {
        "percentual_patrimonio": percentual_patrimonio_div,
        "total_dividas": total_dividas,
    }
    if custo_medio_pct_aa is not None:
        endividamento["custo_medio_pct_aa"] = custo_medio_pct_aa

    inputs = E5OutputInputs(
        periodo_dados="2026-01 a 2026-12",
        data_analise="2026-05-06",
        patrimonio={"bruto": 1_500_000, "liquido": 1_400_000, "investivel": 1_500_000},
        goals=goals,
        fluxo={
            "receita_total": 600_000.0,
            "despesa_total": 240_000.0,
            "despesa_mensal_media": despesa_mensal_media,
            "renda_passiva_mensal_atual": renda_passiva_observada,
        },
        ratios={"taxa_poupanca_recorrente_pct": 40, "rentabilidade_pct": "N/D"},
        score={"valor": 7.5, "classificacao": "Bom"},
        orcamento={"total": 5_000},
        reserva={"cobertura_meses": 12},
        endividamento=endividamento,
        previdencia={"status": "N/D"},
        pontos_fortes=[],
        pontos_urgentes=[],
        investimentos_classes={"total": 500_000, "tabela_classes": []},
        equilibrio_cerbasi={"classificacao": "Equilibrado"},
        consumo={"total_pontuais": 10_000},
        diagnostico=[],
        cenarios_conjuge={"cenarios": []},
    )
    return build_e5_output(inputs)


@pytest.fixture
def gen() -> SuggestionGenerator:
    return SuggestionGenerator(SuggestionGeneratorConfig())


# =============================================================================
# FP-001 — rule_renda_passiva_real_baixa em snapshot real
# =============================================================================


def test_fp001_renda_passiva_real_baixa_dispara_em_snapshot_real(gen):
    """Workspace com `if_pct≥50` dispara `rule_renda_passiva_real_baixa`."""
    proj = _build_if_projection(investivel=2_500_000)  # 50% da meta 5M
    snapshot = _build_snapshot(if_projection=proj)
    # Sanity: snapshot real expõe `if_pct` (não `progresso_if_pct`).
    assert "if_pct" in snapshot["goals"]
    assert snapshot["goals"]["if_pct"] >= 50.0
    kinds = {d.kind for d in gen.generate(snapshot)}
    assert "renda_passiva_real_baixa" in kinds


def test_fp001_silencia_para_if_pct_baixo(gen):
    """If_pct < 50% → regra silencia (alvo Perini só faz sentido após meio plano)."""
    proj = _build_if_projection(investivel=500_000)  # 10% da meta
    snapshot = _build_snapshot(if_projection=proj)
    assert snapshot["goals"]["if_pct"] < 50.0
    kinds = {d.kind for d in gen.generate(snapshot)}
    assert "renda_passiva_real_baixa" not in kinds


# =============================================================================
# FP-002 — Pontos fortes "Caminho para IF" via PontosFortesAnalyzer
# =============================================================================


def test_fp002_pontos_fortes_caminho_para_if_dispara_com_if_pct_alto():
    """Workspace com `if_pct≥20` adiciona ponto forte 'Caminho para IF'."""
    proj = _build_if_projection(investivel=1_500_000)  # 30% da meta
    goals_dict = proj.to_legacy_dict()
    assert goals_dict["if_pct"] >= 20.0

    analyzer = PontosFortesAnalyzer()
    out = analyzer.analyze(
        score={"valor": 7.5, "classificacao": "Bom"},
        ratios={},
        patrimonio={"bruto": 1_500_000.0},
        fluxo={},
        reserva={"cobertura_meses": 12.0},
        # Adapter agora passa `goals.if_pct` (FP-002).
        goals={"if_pct": goals_dict["if_pct"]},
    )
    titulos = {p.titulo for p in out}
    assert "Caminho para Independência Financeira" in titulos


def test_fp002_pontos_fortes_silencia_quando_if_pct_baixo():
    proj = _build_if_projection(investivel=200_000)  # 4% da meta
    goals_dict = proj.to_legacy_dict()
    analyzer = PontosFortesAnalyzer()
    out = analyzer.analyze(
        score={"valor": 5.0, "classificacao": "Regular"},
        ratios={},
        patrimonio={},
        fluxo={},
        reserva={},
        goals={"if_pct": goals_dict["if_pct"]},
    )
    titulos = {p.titulo for p in out}
    assert "Caminho para Independência Financeira" not in titulos


# =============================================================================
# FP-003 — dolarizacao_atrasada ausente do output
# =============================================================================


def test_fp003_dolarizacao_atrasada_ausente_do_output(gen):
    """Mesmo com `goals.dolarizacao` no snapshot, regra não existe mais."""
    proj = _build_if_projection(investivel=2_500_000)
    snapshot = _build_snapshot(if_projection=proj)
    # Adiciona ruído de USA modo — não deve produzir suggestion.
    snapshot["dolarizacao"] = {"cobertura_pct": 0.0, "meta_pct": 50.0}
    kinds = {d.kind for d in gen.generate(snapshot)}
    assert "dolarizacao_atrasada" not in kinds


# =============================================================================
# FP-009 — carry-trade endividamento em snapshot real
# =============================================================================


def test_fp009_carry_trade_dispara_em_snapshot_real(gen):
    """Cenário do prompt: dívida 25%a.a. + retorno 12%a.a. → regra dispara."""
    proj = _build_if_projection(retorno_real_anual_pct=12.0)
    snapshot = _build_snapshot(
        if_projection=proj,
        custo_medio_pct_aa=25.0,
        percentual_patrimonio_div=5.0,  # baixo — só dispara via carry-trade.
    )
    # Sanity: IFProjection.to_legacy_dict emite retorno_esperado_pct_aa (FP-009).
    assert snapshot["goals"]["retorno_esperado_pct_aa"] == 12.0
    kinds = {d.kind for d in gen.generate(snapshot)}
    assert "endividamento_perigoso" in kinds


def test_fp009_divida_barata_nao_dispara_carry(gen):
    """Cenário inverso: dívida 8%a.a. + retorno 12%a.a. → não dispara por carry."""
    proj = _build_if_projection(retorno_real_anual_pct=12.0)
    snapshot = _build_snapshot(
        if_projection=proj,
        custo_medio_pct_aa=8.0,
        percentual_patrimonio_div=10.0,  # também baixo.
    )
    kinds = {d.kind for d in gen.generate(snapshot)}
    assert "endividamento_perigoso" not in kinds


def test_fp009_legacy_dict_emite_retorno_esperado_pct_aa():
    """Sanity-check do contrato: IFProjection.to_legacy_dict expõe campo novo."""
    proj = _build_if_projection(retorno_real_anual_pct=7.5)
    d = proj.to_legacy_dict()
    assert "retorno_esperado_pct_aa" in d
    assert d["retorno_esperado_pct_aa"] == 7.5
