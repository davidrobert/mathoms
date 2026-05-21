"""Goldens + gates — `cascata_calculator.compute` (ADR-236 §D3 · 4 regimes V1 + gates da ADR)."""

from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pipeline.domain.models.transaction import Money  # noqa: E402
from pipeline.domain.services.tributario.cascata_calculator import (  # noqa: E402
    SIMPLES_ANEXO_III,
    SIMPLES_ANEXO_V,
    CascataInput,
    CascataOutput,
    CascataTrigger,
    compute,
    compute_irrf_mensal,
    compute_simples_aliquota_efetiva,
)

# Tolerância de comparação ≤ 1 centavo (arredondamento entre passos da cascata).
_TOL = Decimal("0.02")


def _approx(actual: Money, expected: str) -> bool:
    return abs(actual.amount - Decimal(expected)) <= _TOL


def _trigger_codes(out: CascataOutput) -> set[str]:
    return {t.code for t in out.triggers}


# =============================================================================
# Helpers progressivos (sanity das tabelas)
# =============================================================================


def test_irrf_isento_abaixo_da_faixa_1():
    assert compute_irrf_mensal(Money.brl("2000")).amount == Decimal("0")


def test_irrf_faixa_topo_aplica_aliquota_275():
    # 10.000 mensal: 10000 × 0,275 − 908,73 = 1841,27
    irrf = compute_irrf_mensal(Money.brl("10000"))
    assert irrf.amount == Decimal("1841.27")


def test_simples_iii_faixa_3_alquota_efetiva():
    # RBT12 = 600k, faixa 3 (limite 720k): 13,5% − 17.640
    # efetiva = (600000 × 0,135 − 17640) / 600000 = 0,1056
    efetiva = compute_simples_aliquota_efetiva(Money.brl("600000"), SIMPLES_ANEXO_III)
    assert efetiva == Decimal("0.1056")


def test_simples_v_faixa_3_alquota_efetiva():
    # RBT12 = 600k, Anexo V faixa 3: 19,5% − 9.900
    # efetiva = (600000 × 0,195 − 9900) / 600000 = 0,1785
    efetiva = compute_simples_aliquota_efetiva(Money.brl("600000"), SIMPLES_ANEXO_V)
    assert efetiva == Decimal("0.1785")


# =============================================================================
# GOLDEN 1 — Simples Nacional Anexo III (fator-R OK)
# =============================================================================


def _input_simples_iii() -> CascataInput:
    # Sócio tech: receita R$ 600k, pró-labore R$ 12k/mês, folha PJ R$ 6k/mês.
    # Fator-R = (12k+6k)×12/600k = 36% → ≥28% → Anexo III correto.
    return CascataInput(
        regime="simples",
        anexo_simples="III",
        iss_aliquota_pct=None,
        tipo_declaracao_ir="completa",
        receita_pj_anual=Money.brl("600000"),
        pro_labore_mensal=Money.brl("12000"),
        lucros_distribuidos_mensal=Money.brl("20000"),
        folha_pj_mensal=Money.brl("6000"),
        outras_rendas_tributaveis_pf_anual=Money.brl("0"),
    )


def test_golden_simples_iii_header():
    out = compute(_input_simples_iii())
    assert out.regime == "simples"
    assert out.regime_label == "Simples Nacional — Anexo III"
    assert out.regime_nao_suportado is False


def test_golden_simples_iii_tributos():
    out = compute(_input_simples_iii())
    # DAS = 600.000 × 0,1056 = R$ 63.360
    assert _approx(out.tributos_federais, "63360.00")
    assert out.iss_total.amount == Decimal("0")  # Simples inclui ISS no DAS
    # Pró-labore anual = 12.000 × 12 = R$ 144.000
    assert _approx(out.pro_labore_bruto, "144000.00")
    # INSS patronal = 0 (Simples inclui no DAS); INSS empregado 11% até teto
    assert out.inss_patronal.amount == Decimal("0")
    assert _approx(out.inss_empregado, "10767.78")
    # IRRF anual: (12000 − 897,32) × 0,275 − 908,73 = 2.144,51 → × 12 = 25.734,12
    assert _approx(out.irrf_pro_labore, "25734.12")
    # Lucro contábil = 600000 − 63360 − 144000 = R$ 392.640
    assert _approx(out.lucro_contabil_pj, "392640.00")
    assert _approx(out.lucros_distribuidos, "240000.00")


def test_golden_simples_iii_pgbl():
    out = compute(_input_simples_iii())
    # Base PGBL = pró-labore bruto + outras tributáveis = 144.000 + 0
    assert _approx(out.pgbl_base_anual, "144000.00")
    # Limite = 144.000 × 0,12 = R$ 17.280
    assert _approx(out.pgbl_limite_anual, "17280.00")
    assert out.pgbl_aplicavel is True
    assert out.pgbl_motivo_inaplicavel is None


def test_golden_simples_iii_fator_r():
    out = compute(_input_simples_iii())
    # (12000 + 6000) × 12 / 600000 = 0,36 = 36%
    assert out.fator_r_pct == Decimal("0.36")
    assert out.fator_r_faixa == "anexo_iii"
    # Break-even = max(0, 0,28 × 600000 − 216000) / 12 = max(0, -48000) / 12 = 0
    assert out.fator_r_break_even_mensal is not None
    assert out.fator_r_break_even_mensal.amount == Decimal("0")


def test_golden_simples_iii_triggers():
    out = compute(_input_simples_iii())
    # T1: pro_labore 12k ≥ 8157,41 → NÃO dispara
    # T2: fator-R 36%, distância 8pp > 5pp → NÃO dispara
    # T3: PGBL aplicável + IR marginal 27,5% ≥ 22,5% → DISPARA
    # T4: 0 imóveis → NÃO dispara
    # T5: 600k < 80%×3,6M = 2,88M → NÃO dispara
    assert _trigger_codes(out) == {"T3"}


# =============================================================================
# GOLDEN 2 — Simples Nacional Anexo V (fator-R baixo + T1 + T3)
# =============================================================================


def _input_simples_v() -> CascataInput:
    # Mesmo receita 600k mas pró-labore baixo (5k) e zero folha → fator-R 10% → V.
    return CascataInput(
        regime="simples",
        anexo_simples="V",
        iss_aliquota_pct=None,
        tipo_declaracao_ir="completa",
        receita_pj_anual=Money.brl("600000"),
        pro_labore_mensal=Money.brl("5000"),
        lucros_distribuidos_mensal=Money.brl("30000"),
        folha_pj_mensal=Money.brl("0"),
        outras_rendas_tributaveis_pf_anual=Money.brl("0"),
    )


def test_golden_simples_v_cascata():
    out = compute(_input_simples_v())
    assert out.regime_label == "Simples Nacional — Anexo V"
    # DAS Anexo V faixa 3: 600.000 × 0,1785 = R$ 107.100
    assert _approx(out.tributos_federais, "107100.00")
    # Pró-labore anual = 5.000 × 12 = R$ 60.000
    assert _approx(out.pro_labore_bruto, "60000.00")
    # INSS empregado = 5000 × 0,11 × 12 = R$ 6.600
    assert _approx(out.inss_empregado, "6600.00")
    # IRRF base = 5000 − 550 = 4.450 → faixa 4: 0,225 × 4450 − 675,49 = 325,76 → ann 3.909,12
    assert _approx(out.irrf_pro_labore, "3909.12")
    # Lucro contábil = 600000 − 107100 − 60000 = R$ 432.900
    assert _approx(out.lucro_contabil_pj, "432900.00")


def test_golden_simples_v_fator_r():
    out = compute(_input_simples_v())
    # 60.000 / 600.000 = 0,10 = 10% → Anexo V
    assert out.fator_r_pct == Decimal("0.10")
    assert out.fator_r_faixa == "anexo_v"
    # Break-even: 0,28 × 600000 − 60000 = 108.000 anual / 12 = R$ 9.000/mês
    assert _approx(out.fator_r_break_even_mensal, "9000.00")


def test_golden_simples_v_triggers():
    out = compute(_input_simples_v())
    # T1: pro_labore 5000 < 8157,41 → DISPARA (PGBL sub-ocupado)
    # T2: fator-R 10%, distância 18pp > 5pp → NÃO dispara
    # T3: PGBL aplicável + IR marginal 27,5% ≥ 22,5% → DISPARA
    assert _trigger_codes(out) == {"T1", "T3"}


# =============================================================================
# GOLDEN 3 — Lucro Presumido com ISS destacado + aluguéis (T3 + T4)
# =============================================================================


def _input_presumido() -> CascataInput:
    return CascataInput(
        regime="lucro_presumido",
        anexo_simples=None,
        iss_aliquota_pct=Decimal("5"),
        tipo_declaracao_ir="completa",
        receita_pj_anual=Money.brl("1200000"),
        pro_labore_mensal=Money.brl("10000"),
        lucros_distribuidos_mensal=Money.brl("0"),
        folha_pj_mensal=Money.brl("0"),
        outras_rendas_tributaveis_pf_anual=Money.brl("120000"),  # aluguéis
        imoveis_alugados_count=4,
        receita_aluguel_anual=Money.brl("120000"),
    )


def test_golden_presumido_cascata():
    out = compute(_input_presumido())
    assert out.regime_label == "Lucro Presumido"
    # PIS+COFINS+IRPJ+adicional+CSLL = 7800+36000+72000+34560 = R$ 150.360
    assert _approx(out.tributos_federais, "150360.00")
    # ISS = 1.200.000 × 0,05 = R$ 60.000
    assert _approx(out.iss_total, "60000.00")
    # Pró-labore anual = 120.000
    assert _approx(out.pro_labore_bruto, "120000.00")
    # INSS patronal (Presumido): 10000 × 0,20 × 12 = R$ 24.000
    assert _approx(out.inss_patronal, "24000.00")
    # INSS empregado: 897,32 × 12 = R$ 10.767,78
    assert _approx(out.inss_empregado, "10767.78")
    # IRRF: base mensal 9.102,68 × 0,275 − 908,73 = 1594,51 → anual 19.134,12
    assert _approx(out.irrf_pro_labore, "19134.12")
    # Lucro contábil = 1200000 − 150360 − 60000 − 120000 − 24000 = R$ 845.640
    assert _approx(out.lucro_contabil_pj, "845640.00")


def test_golden_presumido_pgbl():
    out = compute(_input_presumido())
    # Base = 120.000 (pró-labore) + 120.000 (aluguéis) = R$ 240.000
    assert _approx(out.pgbl_base_anual, "240000.00")
    assert _approx(out.pgbl_limite_anual, "28800.00")
    assert out.pgbl_aplicavel is True


def test_golden_presumido_no_fator_r():
    out = compute(_input_presumido())
    # Fator-R só Simples
    assert out.fator_r_pct is None
    assert out.fator_r_faixa is None


def test_golden_presumido_triggers():
    out = compute(_input_presumido())
    # T1: pro_labore 10k ≥ 8157,41 → NÃO dispara
    # T2: N/A (não-Simples)
    # T3: IR marginal 27,5% ≥ 22,5% → DISPARA
    # T4: 4 imóveis ≥ 3 + 120k ≥ 90k → DISPARA
    # T5: N/A (não-Simples)
    assert _trigger_codes(out) == {"T3", "T4"}


# =============================================================================
# GOLDEN 4 — MEI (DAS fixo + sem cascata complexa)
# =============================================================================


def test_golden_mei_cascata():
    out = compute(
        CascataInput(
            regime="mei",
            tipo_declaracao_ir="completa",
            receita_pj_anual=Money.brl("60000"),
            pro_labore_mensal=Money.brl("0"),
            lucros_distribuidos_mensal=Money.brl("4500"),
        )
    )
    assert out.regime == "mei"
    assert out.regime_label == "MEI"
    assert out.regime_nao_suportado is False
    # DAS-MEI serviços R$ 79,90 × 12 = R$ 958,80
    assert _approx(out.tributos_federais, "958.80")
    assert out.iss_total.amount == Decimal("0")
    # PGBL base = 0 (pró-labore 0 + outras 0) → não aplicável
    assert out.pgbl_base_anual.amount == Decimal("0")
    assert out.pgbl_aplicavel is False
    assert out.pgbl_motivo_inaplicavel == "renda_tributavel_pf_zerada"


# =============================================================================
# Workspace incompleto + Lucro Real (estados de fallback)
# =============================================================================


def test_workspace_incompleto_regime_none():
    out = compute(CascataInput(regime=None))
    assert out.regime is None
    assert out.regime_nao_suportado is True
    assert out.motivo_nao_suportado == "perfil_incompleto"
    assert out.regime_label == "Perfil tributário incompleto"
    assert out.triggers == ()


def test_workspace_incompleto_simples_sem_anexo():
    out = compute(CascataInput(regime="simples", anexo_simples=None))
    assert out.regime_nao_suportado is True
    assert out.motivo_nao_suportado == "anexo_simples_pendente"


def test_lucro_real_nao_suportado():
    out = compute(
        CascataInput(
            regime="lucro_real",
            receita_pj_anual=Money.brl("5000000"),
            pro_labore_mensal=Money.brl("20000"),
        )
    )
    assert out.regime == "lucro_real"
    assert out.regime_label == "Lucro Real"
    assert out.regime_nao_suportado is True
    assert out.motivo_nao_suportado == "lucro_real"
    assert out.triggers == ()


# =============================================================================
# Gates explícitos da ADR-236
# =============================================================================


def test_pgbl_base_is_renda_tributavel_pf_not_receita_pj_times_32pct():
    """Gate crítico — base PGBL nunca é `receita_pj × 32%` (folclore amador rejeitado)."""
    # Workspace típico: receita PJ R$ 600k, pró-labore R$ 5k/mês, sem aluguéis.
    out = compute(_input_simples_v())
    pro_labore_anual = Decimal("60000")
    # Confusão amador comum (rejeitada):
    receita_pj_x_32pct = Decimal("600000") * Decimal("0.32")  # = 192.000
    # Base PGBL canônica = pró-labore + outras tributáveis (= 60.000 aqui).
    assert _approx(out.pgbl_base_anual, str(pro_labore_anual))
    # Confirmação explícita: NUNCA pode ser receita × 32%.
    assert out.pgbl_base_anual.amount != receita_pj_x_32pct


def _input_simples_iii_simplificada() -> CascataInput:
    base = _input_simples_iii()
    return CascataInput(
        regime=base.regime,
        anexo_simples=base.anexo_simples,
        tipo_declaracao_ir="simplificada",
        receita_pj_anual=base.receita_pj_anual,
        pro_labore_mensal=base.pro_labore_mensal,
        lucros_distribuidos_mensal=base.lucros_distribuidos_mensal,
        folha_pj_mensal=base.folha_pj_mensal,
        outras_rendas_tributaveis_pf_anual=base.outras_rendas_tributaveis_pf_anual,
    )


def test_simplificada_anula_pgbl():
    out = compute(_input_simples_iii_simplificada())
    assert out.pgbl_base_anual.amount > Decimal("0")  # renda tributável existe
    assert out.pgbl_aplicavel is False
    assert out.pgbl_motivo_inaplicavel == "declaracao_simplificada"


def test_simplificada_bloqueia_triggers_pgbl_dependentes():
    out = compute(_input_simples_iii_simplificada())
    codes = _trigger_codes(out)
    assert "T1" not in codes  # T1 exige PGBL aplicável
    assert "T3" not in codes  # T3 exige PGBL aplicável


def test_triggers_break_even_computed():
    # Gate — todo trigger emitido tem params com valor numérico (não copy genérico).
    out = compute(_input_simples_v())
    assert len(out.triggers) >= 2
    for trigger in out.triggers:
        assert isinstance(trigger, CascataTrigger)
        assert trigger.params, f"Trigger {trigger.code} sem params"
        # Cada trigger documenta pelo menos um valor numérico de break-even/threshold.
        has_numeric = any(
            isinstance(v, (int, str))
            and (isinstance(v, int) or v.replace(".", "").replace("-", "").isdigit())
            for v in trigger.params.values()
        )
        assert has_numeric, f"Trigger {trigger.code} sem valor numérico em params"


def test_no_holding_trigger_zero_imoveis_mesmo_receita_pj_alta():
    # Gate anti-folclore — receita PJ enorme + 0 imóveis NÃO dispara T4.
    inp = CascataInput(
        regime="lucro_presumido",
        iss_aliquota_pct=Decimal("5"),
        receita_pj_anual=Money.brl("3000000"),
        pro_labore_mensal=Money.brl("10000"),
        outras_rendas_tributaveis_pf_anual=Money.brl("120000"),
        imoveis_alugados_count=0,
        receita_aluguel_anual=Money.brl("0"),
    )
    assert "T4" not in _trigger_codes(compute(inp))


def test_no_holding_trigger_dois_imoveis_abaixo_min():
    # Gate anti-folclore — 2 imóveis (< T4_IMOVEIS_MIN=3) NÃO dispara T4.
    inp = CascataInput(
        regime="lucro_presumido",
        iss_aliquota_pct=Decimal("5"),
        receita_pj_anual=Money.brl("1200000"),
        pro_labore_mensal=Money.brl("10000"),
        outras_rendas_tributaveis_pf_anual=Money.brl("120000"),
        imoveis_alugados_count=2,
        receita_aluguel_anual=Money.brl("120000"),
    )
    assert "T4" not in _trigger_codes(compute(inp))


def test_trigger_t5_proximo_sublimite_simples():
    """T5 dispara quando receita PJ ≥ 80% do sublimite nacional R$ 3,6M."""
    inp = CascataInput(
        regime="simples",
        anexo_simples="III",
        receita_pj_anual=Money.brl("3000000"),
        pro_labore_mensal=Money.brl("15000"),
        folha_pj_mensal=Money.brl("60000"),  # fator-R ~30% → seguro de T2
        outras_rendas_tributaveis_pf_anual=Money.brl("0"),
    )
    out = compute(inp)
    assert "T5" in _trigger_codes(out)
    t5 = next(t for t in out.triggers if t.code == "T5")
    # Break-even: distância para o sublimite R$ 3,6M.
    assert Decimal(t5.params["distancia_brl"]) == Decimal("600000.00")


def test_trigger_t2_fator_r_proximo_corte():
    """T2 dispara quando |fator_r − 28%| < 5pp."""
    # Fator-R = 25%: distância 3pp < 5pp → DISPARA
    inp = CascataInput(
        regime="simples",
        anexo_simples="V",
        receita_pj_anual=Money.brl("600000"),
        pro_labore_mensal=Money.brl("10500"),  # 10500×12=126k; folha 0 → 21%
        folha_pj_mensal=Money.brl("2000"),  # +24k → 150k total → 25%
        outras_rendas_tributaveis_pf_anual=Money.brl("0"),
    )
    out = compute(inp)
    assert "T2" in _trigger_codes(out)
    t2 = next(t for t in out.triggers if t.code == "T2")
    # Break-even mensal = (0,28 × 600k − 150k) / 12 = (168k − 150k) / 12 = R$ 1.500
    assert Decimal(t2.params["delta_folha_mensal_brl"]) == Decimal("1500.00")
