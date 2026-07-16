"""Unit tests — Onda 2 (ADR-216) cap rate líquido + tríade benchmarks + cascade D9."""

from __future__ import annotations

import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.domain.services.real_estate_metrics import (
    INVESTMENT_CLASSIFICATIONS,
    Alerta,
    BenchmarkRates,
    ComponenteCalculo,
    ExcludedProperty,
    PropertyInput,
    PropertyMetrics,
    RealEstateConfig,
    RealEstateMetricsResult,
    _confidence_for,
    calculate_real_estate_metrics,
    filter_investment_properties,
    result_to_payload,
)


def _benchmarks(cdi: str = "8.7", ntnb: str = "5.5", ifix: str = "9.2") -> BenchmarkRates:
    return BenchmarkRates(
        cdi_liquido_pct=Decimal(cdi),
        ntnb_liquido_pct=Decimal(ntnb),
        ifix_yield_pct=Decimal(ifix),
        as_of_date=date(2026, 5, 15),
    )


def _property(
    *,
    property_id: str = "p1",
    descricao: str = "Apto",
    classification: str = "locado",
    valor: str = "1200000",
    aluguel: str | None = "25200",
    aluguel_origem: str = "informe",
    taxa_adm: str | None = "2520",
    ir_retido: str = "0",
    ir_carne_leao: str | None = None,
    iptu: str | None = "4800",
    iptu_origem: str = "informe",
    condominio: str | None = None,
    meses_locado: int | None = 12,
    meses_desde_reajuste: int | None = None,
) -> PropertyInput:
    return PropertyInput(
        property_id=property_id,
        descricao=descricao,
        classification=classification,
        valor_imovel=Decimal(valor),
        aluguel_bruto_anual=Decimal(aluguel) if aluguel is not None else None,
        aluguel_origem=aluguel_origem,
        taxa_administracao_anual=Decimal(taxa_adm) if taxa_adm is not None else None,
        ir_retido_anual=Decimal(ir_retido),
        ir_carne_leao_anual=Decimal(ir_carne_leao) if ir_carne_leao is not None else None,
        iptu_anual=Decimal(iptu) if iptu is not None else None,
        iptu_origem=iptu_origem,
        condominio_anual=Decimal(condominio) if condominio is not None else None,
        meses_locado_no_ano=meses_locado,
        meses_desde_ultimo_reajuste=meses_desde_reajuste,
    )


# ────────────────────────── INVESTMENT_CLASSIFICATIONS ─────────────────────


def test_investment_classifications_alinha_com_pr281_enum():
    """ADR-216 D8 + ADR-215 enum — só 3 classes contam como investimento."""
    assert INVESTMENT_CLASSIFICATIONS == ("locado", "comercial", "especulacao")


def test_filter_investment_properties_segrega_residencia_e_uso_pessoal():
    props = [
        _property(property_id="p1", classification="locado"),
        _property(property_id="p2", classification="residencia_principal"),
        _property(property_id="p3", classification="uso_pessoal"),
        _property(property_id="p4", classification="comercial"),
        _property(property_id="p5", classification="especulacao"),
        _property(property_id="p6", classification="desconhecido"),
        # ADR-235: nu_proprietario fora do denominador de cap rate
        _property(property_id="p7", classification="nu_proprietario"),
    ]
    investment, excluded = filter_investment_properties(props)

    assert {p.property_id for p in investment} == {"p1", "p4", "p5"}
    assert {e.property_id for e in excluded} == {"p2", "p3", "p6", "p7"}
    motivos = {e.classification: e.motivo for e in excluded}
    assert "Residência principal" in motivos["residencia_principal"]
    assert "uso pessoal" in motivos["uso_pessoal"].lower()
    assert "pendente" in motivos["desconhecido"].lower()


def test_nu_proprietario_nao_entra_em_investment_classifications():
    """ADR-235: nu_proprietario fora de INVESTMENT_CLASSIFICATIONS — cap rate
    indefinido (não puxa média do portfolio pra baixo).
    """
    assert "nu_proprietario" not in INVESTMENT_CLASSIFICATIONS


# ────────────────────────── _confidence_for cascade ────────────────────────


def test_confidence_high_para_informe_e_manual():
    assert _confidence_for("informe") == "high"
    assert _confidence_for("manual") == "high"


def test_confidence_medium_para_irpf_e3_e4():
    assert _confidence_for("irpf") == "medium"
    assert _confidence_for("e3") == "medium"
    assert _confidence_for("e4") == "medium"


def test_confidence_low_para_default_e_pro_rata():
    assert _confidence_for("default") == "low"
    assert _confidence_for("pro_rata") == "low"
    assert _confidence_for("none") == "low"


# ────────────────────────── Cap rate por imóvel ────────────────────────────


def test_cap_rate_bruto_calc_canonical():
    """`cap_rate_bruto = aluguel_anual / valor × 100` — FORMULAS.md §Imóveis."""
    p = _property(valor="1200000", aluguel="25200", meses_locado=12)
    result = calculate_real_estate_metrics(
        [p],
        concentracao_imobiliaria_pct=Decimal("30"),
        benchmarks=_benchmarks(),
    )
    # 25200 / 1200000 = 2.1%
    assert result.cap_rate_bruto_pct == Decimal("2.10")
    assert result.imoveis[0].cap_rate_bruto_pct == Decimal("2.10")


def test_cap_rate_liquido_subtrai_todos_componentes():
    """Liquido = bruto - taxa_adm - ir_retido - ir_carne_leao - iptu - cond - manut - vacancia."""
    p = _property(
        valor="1000000",
        aluguel="60000",
        taxa_adm="6000",
        ir_retido="0",
        iptu="3600",
        condominio="0",
        meses_locado=12,  # vacancia empírica = 0
    )
    config = RealEstateConfig(
        manutencao_pct=Decimal("0.01"),  # 1% × 1M = 10000
        ir_carne_leao_fallback_pct=Decimal("0.275"),  # 27.5% × 60000 = 16500
    )
    result = calculate_real_estate_metrics(
        [p],
        concentracao_imobiliaria_pct=Decimal("30"),
        benchmarks=_benchmarks(),
        config=config,
    )
    # liquido = 60000 - 6000 - 0 - 16500 - 3600 - 0 - 10000 - 0 = 23900
    # cap_rate_liquido = 23900 / 1000000 = 2.39%
    assert result.cap_rate_liquido_pct == Decimal("2.39")


def test_cap_rate_liquido_usa_irpf_quando_informado():
    """`ir_carne_leao_anual` informado (irpf) sobrescreve fallback 27,5%."""
    p = _property(
        valor="1000000",
        aluguel="60000",
        taxa_adm="0",
        iptu="0",
        meses_locado=12,
        ir_carne_leao="9000",  # irpf marginal real
    )
    config = RealEstateConfig(manutencao_pct=Decimal("0.0"), vacancia_pct=Decimal("0.0"))
    result = calculate_real_estate_metrics(
        [p],
        concentracao_imobiliaria_pct=Decimal("30"),
        benchmarks=_benchmarks(),
        config=config,
    )
    # 60000 - 9000 = 51000 → 5.10%
    assert result.cap_rate_liquido_pct == Decimal("5.10")
    # Origem do IR carnê-leão é "irpf" (não default)
    assert result.componentes_calculo["ir_carne_leao_anual"].origem == "irpf"


def test_vacancia_empirica_sobrescreve_default():
    """Quando informe traz `meses_locado < 12`, vacância empírica vence default 15%."""
    p = _property(
        valor="1200000",
        aluguel="24000",
        meses_locado=8,  # vagou 4 meses
        taxa_adm="0",
        iptu="0",
    )
    config = RealEstateConfig(
        manutencao_pct=Decimal("0.0"),
        vacancia_pct=Decimal("0.15"),  # default que NÃO deve ser usado
        ir_carne_leao_fallback_pct=Decimal("0.0"),
    )
    result = calculate_real_estate_metrics(
        [p],
        concentracao_imobiliaria_pct=Decimal("30"),
        benchmarks=_benchmarks(),
        config=config,
    )
    imovel = result.imoveis[0]
    # Empírica = (12-8)/12 = 33.33%
    assert imovel.vacancia_pct_empirica == Decimal("33.33")
    # vacancia_anual_brl = 24000 × 4/12 = 8000 (não 24000×0.15=3600)
    assert result.componentes_calculo["vacancia_anual"].valor == Decimal("8000.00")
    assert result.componentes_calculo["vacancia_anual"].origem == "informe"


def test_vacancia_default_quando_meses_locado_none():
    """Sem `meses_locado` (informe ausente) → default 15%."""
    p = _property(
        valor="1200000",
        aluguel="24000",
        meses_locado=None,
        taxa_adm="0",
        iptu="0",
    )
    config = RealEstateConfig(
        manutencao_pct=Decimal("0.0"), ir_carne_leao_fallback_pct=Decimal("0.0")
    )
    result = calculate_real_estate_metrics(
        [p],
        concentracao_imobiliaria_pct=Decimal("30"),
        benchmarks=_benchmarks(),
        config=config,
    )
    # 24000 × 15% = 3600
    assert result.componentes_calculo["vacancia_anual"].valor == Decimal("3600.00")
    assert result.componentes_calculo["vacancia_anual"].origem == "default"


def test_imovel_sem_aluguel_marca_sem_renda():
    """`aluguel_bruto = None` ou 0 → status `sem_renda` + cap_rate None."""
    p = _property(aluguel=None)
    result = calculate_real_estate_metrics(
        [p], concentracao_imobiliaria_pct=Decimal("30"), benchmarks=_benchmarks()
    )
    imovel = result.imoveis[0]
    assert imovel.status_contrato == "sem_renda"
    assert imovel.cap_rate_bruto_pct is None
    assert imovel.cap_rate_liquido_pct is None


def test_status_contrato_reajuste_pendente():
    """Imóvel com contrato sem reajuste > 12 meses → status `reajuste_pendente`."""
    p = _property(meses_desde_reajuste=18)
    result = calculate_real_estate_metrics(
        [p], concentracao_imobiliaria_pct=Decimal("30"), benchmarks=_benchmarks()
    )
    assert result.imoveis[0].status_contrato == "reajuste_pendente"


# ────────────────────────── Concentração ───────────────────────────────────


def test_concentracao_pct_passthrough_do_canonico():
    """C11-Fase2 (ADR-340): o serviço não computa mais concentração — ecoa o
    canônico injetado (SSOT = compute_concentracao_imobiliaria_pct em ratios).
    A fórmula cat_2/carteira é testada em tests/test_concentracao_imobiliaria.py."""
    props = [
        _property(property_id="p1", valor="1200000"),
        _property(property_id="p2", valor="800000"),
    ]
    result = calculate_real_estate_metrics(
        props, concentracao_imobiliaria_pct=Decimal("60"), benchmarks=_benchmarks()
    )
    assert result.concentracao_pct == Decimal("60.00")


def test_residencia_principal_excluida_da_tabela_de_investimento():
    """Residência principal NÃO entra na tabela de imóveis de investimento (D8)."""
    props = [
        _property(property_id="p1", valor="1000000", classification="locado"),
        _property(property_id="p2", valor="2000000", classification="residencia_principal"),
    ]
    result = calculate_real_estate_metrics(
        props, concentracao_imobiliaria_pct=Decimal("30"), benchmarks=_benchmarks()
    )
    assert len(result.excluded_properties) == 1


# ────────────────────────── Benchmarks + spreads ───────────────────────────


def test_spreads_pp_assinados_e_brl_anual():
    """spread_pp = cap_rate - benchmark (sinal natural); spread_brl = valor_total × spread / 100."""
    p = _property(valor="1000000", aluguel="20000", taxa_adm="0", iptu="0", meses_locado=12)
    config = RealEstateConfig(
        manutencao_pct=Decimal("0.0"), ir_carne_leao_fallback_pct=Decimal("0.0")
    )
    result = calculate_real_estate_metrics(
        [p],
        concentracao_imobiliaria_pct=Decimal("30"),
        benchmarks=_benchmarks(cdi="8.7", ntnb="5.5", ifix="9.2"),
        config=config,
    )
    # cap_rate_liquido = 20000/1000000 = 2.0%
    assert result.cap_rate_liquido_pct == Decimal("2.00")
    # spread vs cdi = 2.0 - 8.7 = -6.7
    assert result.spreads_pp["vs_cdi"] == Decimal("-6.70")
    # spread_brl = 1000000 × -6.7 / 100 = -67000
    assert result.spread_brl_anual["vs_cdi"] == Decimal("-67000.00")
    assert result.spreads_pp["vs_ntnb"] == Decimal("-3.50")
    assert result.spreads_pp["vs_ifix"] == Decimal("-7.20")


def test_benchmarks_propagados_para_payload():
    p = _property()
    result = calculate_real_estate_metrics(
        [p], concentracao_imobiliaria_pct=Decimal("30"), benchmarks=_benchmarks()
    )
    payload = result_to_payload(result)
    assert payload["benchmarks"]["cdi_liquido_pct"] == 8.7
    assert payload["benchmarks"]["ntnb_liquido_pct"] == 5.5
    assert payload["benchmarks"]["ifix_yield_pct"] == 9.2
    assert payload["benchmarks"]["as_of_date"] == "2026-05-15"


# ────────────────────────── Alertas ────────────────────────────────────────


def test_alerta_concentracao_alta_threshold_50():
    """C11-Fase2 (ADR-340): concentração (base carteira) > 50% dispara concentracao_alta."""
    p = _property(valor="2100000")
    result = calculate_real_estate_metrics(
        [p],
        concentracao_imobiliaria_pct=Decimal("60"),  # > 50
        benchmarks=_benchmarks(),
    )
    codes = [a.code for a in result.alertas]
    assert "concentracao_alta" in codes


def test_alerta_concentracao_nao_dispara_em_50_exato():
    """Threshold é estritamente maior (>), não >=. 50% não dispara."""
    p = _property(valor="2000000")
    result = calculate_real_estate_metrics(
        [p], concentracao_imobiliaria_pct=Decimal("50"), benchmarks=_benchmarks()
    )
    codes = [a.code for a in result.alertas]
    assert "concentracao_alta" not in codes


def test_alerta_spread_critico_combinado():
    """cap_rate < 70% × CDI E concentracao > 45 (co-threshold ADR-340) → spread_critico."""
    # cap rate ~2%; CDI 8.7%; 70% × 8.7 = 6.09; 2 < 6.09 ✓
    p = _property(valor="2000000", aluguel="40000", taxa_adm="0", iptu="0", meses_locado=12)
    config = RealEstateConfig(
        manutencao_pct=Decimal("0.0"), ir_carne_leao_fallback_pct=Decimal("0.0")
    )
    result = calculate_real_estate_metrics(
        [p],
        concentracao_imobiliaria_pct=Decimal("50"),  # 50% > co-threshold 45
        benchmarks=_benchmarks(),
        config=config,
    )
    codes = [a.code for a in result.alertas]
    assert "spread_critico" in codes


def test_alerta_spread_critico_nao_dispara_se_concentracao_baixa():
    """spread baixo MAS concentração < 45 (co-threshold ADR-340) NÃO dispara spread_critico."""
    p = _property(valor="1000000", aluguel="20000", taxa_adm="0", iptu="0", meses_locado=12)
    config = RealEstateConfig(
        manutencao_pct=Decimal("0.0"), ir_carne_leao_fallback_pct=Decimal("0.0")
    )
    result = calculate_real_estate_metrics(
        [p],
        concentracao_imobiliaria_pct=Decimal("30"),  # 30% < co-threshold spread 45 (ADR-340)
        benchmarks=_benchmarks(),
        config=config,
    )
    codes = [a.code for a in result.alertas]
    assert "spread_critico" not in codes


def test_alerta_aluguel_sem_dado_quando_todos_origem_pro_rata():
    """Todos imóveis com `origem == 'pro_rata'` → alerta aluguel_sem_dado."""
    p = _property(aluguel_origem="pro_rata")
    result = calculate_real_estate_metrics(
        [p], concentracao_imobiliaria_pct=Decimal("30"), benchmarks=_benchmarks()
    )
    codes = [a.code for a in result.alertas]
    assert "aluguel_sem_dado" in codes


def test_alerta_contrato_reajuste_pendente_por_imovel():
    """Imóvel com >12 meses sem reajuste gera alerta info por imóvel."""
    p = _property(meses_desde_reajuste=18)
    result = calculate_real_estate_metrics(
        [p], concentracao_imobiliaria_pct=Decimal("30"), benchmarks=_benchmarks()
    )
    codes = [a.code for a in result.alertas]
    assert "contrato_reajuste_pendente" in codes
