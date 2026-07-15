"""Tests — ``RatiosCalculator`` (A5a + A8.3 PR-A passive_income/irpf wiring)."""

from __future__ import annotations

import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.domain.services.irpf_analyzer import IRPFAnalyzer  # noqa: E402
from pipeline.domain.services.passive_income_calculator import (  # noqa: E402
    PassiveIncomeCalculator,
    PassiveIncomeConfig,
    PassiveIncomeResult,
)
from pipeline.domain.services.ratios_calculator import (  # noqa: E402
    FinancialRatios,
    RatiosCalculator,
    RentabilidadeConfig,
    RentabilidadeRatio,
)
from pipeline.llm.schemas.e16_irpf_full import (  # noqa: E402
    CodigoRendimentoIsento,
    CodigoRendimentoTribExclusiva,
    Contribuinte,
    FontePagadoraPJ,
    ImpostoApurado,
    IRPFFullOutput,
    ModeloDeclaracao,
    NaturezaContribuinte,
    RendimentoIsento,
    RendimentoTribExclusiva,
)


def _fluxo_with_janela(*, despesa_mensal_essencial: float = 0.0, **overrides) -> dict:
    base = {
        "receita_recorrente": 120_000,
        "receita_total": 130_000,
        "despesa_total": 60_000,
        "despesa_mensal_media": 5_000,
        "despesa_mensal_essencial": despesa_mensal_essencial,
        "periodo": "2025-04 a 2026-03",
        "n_meses": 12,
    }
    base.update(overrides)
    return {"janela_12m": base}


def _patrimonio(
    bruto: float = 1_000_000,
    dividas: float = 200_000,
    investivel: float = 500_000,
    investivel_efetivo: float | None = None,
) -> dict:
    # `investivel` alimenta `investivel_financeiro` (numerador da autonomia, ADR-335);
    # `investivel_efetivo` diverge só quando o teste quer provar toggle-independência.
    return {
        "bruto": bruto,
        "dividas": dividas,
        "investivel_financeiro": investivel,
        "investivel_efetivo": investivel if investivel_efetivo is None else investivel_efetivo,
    }


class TestTaxaPoupanca:
    def test_recorrente_when_janela_present(self):
        r = RatiosCalculator().calculate(
            _fluxo_with_janela(receita_recorrente=100_000, despesa_total=50_000),
            _patrimonio(),
        )
        # (100k - 50k) / 100k = 50%
        assert r.taxa_poupanca_recorrente_pct == pytest.approx(50.0)

    def test_total_uses_receita_total_not_recorrente(self):
        r = RatiosCalculator().calculate(
            _fluxo_with_janela(
                receita_recorrente=100_000, receita_total=120_000, despesa_total=60_000
            ),
            _patrimonio(),
        )
        # (120k - 60k) / 120k = 50%
        assert r.taxa_poupanca_total_pct == pytest.approx(50.0)

    def test_zero_when_receita_zero(self):
        r = RatiosCalculator().calculate(
            _fluxo_with_janela(receita_recorrente=0, receita_total=0),
            _patrimonio(),
        )
        assert r.taxa_poupanca_recorrente_pct == 0.0
        assert r.taxa_poupanca_total_pct == 0.0


class TestEndividamento:
    def test_percentual_do_bruto(self):
        r = RatiosCalculator().calculate(
            _fluxo_with_janela(),
            _patrimonio(bruto=1_000_000, dividas=200_000),
        )
        assert r.taxa_endividamento_pct == pytest.approx(20.0)

    def test_zero_when_bruto_zero(self):
        r = RatiosCalculator().calculate(
            _fluxo_with_janela(),
            _patrimonio(bruto=0),
        )
        assert r.taxa_endividamento_pct == 0.0


class TestAutonomiaFinanceira:
    """ADR-335: autonomia financeira usa `investivel_financeiro` (sem imóvel ilíquido)."""

    def test_autonomia_meses(self):
        r = RatiosCalculator().calculate(
            _fluxo_with_janela(despesa_mensal_media=5_000),
            _patrimonio(investivel=60_000),
        )
        assert r.autonomia_financeira_meses == pytest.approx(12.0)

    def test_zero_when_despesa_zero(self):
        r = RatiosCalculator().calculate(
            _fluxo_with_janela(despesa_mensal_media=0),
            _patrimonio(),
        )
        assert r.autonomia_financeira_meses == 0.0

    def test_toggle_independente_ignora_investivel_efetivo(self):
        # Duas carteiras idênticas no financeiro, divergindo só no `investivel_efetivo`
        # (proxy do flip `imoveis_no_if`): autonomia NÃO pode mudar (ADR-335 §Precisão).
        toggle_off = RatiosCalculator().calculate(
            _fluxo_with_janela(despesa_mensal_media=5_000),
            _patrimonio(investivel=60_000, investivel_efetivo=60_000),
        )
        toggle_on = RatiosCalculator().calculate(
            _fluxo_with_janela(despesa_mensal_media=5_000),
            _patrimonio(investivel=60_000, investivel_efetivo=260_000),
        )
        assert toggle_on.autonomia_financeira_meses == toggle_off.autonomia_financeira_meses
        assert toggle_on.autonomia_financeira_meses == pytest.approx(12.0)

    def test_legacy_dict_mantem_alias_deprecated(self):
        d = (
            RatiosCalculator()
            .calculate(
                _fluxo_with_janela(despesa_mensal_media=5_000),
                _patrimonio(investivel=60_000),
            )
            .to_legacy_dict()
        )
        assert d["autonomia_financeira_meses"] == pytest.approx(12.0)
        # Alias deprecated por 1 ciclo — mesmo valor.
        assert d["cobertura_despesas_meses"] == d["autonomia_financeira_meses"]


class TestJanela:
    def test_uses_janela_12m_when_present(self):
        r = RatiosCalculator().calculate(
            _fluxo_with_janela(periodo="2025-04 a 2026-03", n_meses=12),
            _patrimonio(),
        )
        assert r.janela_referencia == "2025-04 a 2026-03"
        assert r.janela_n_meses == 12

    def test_falls_back_to_periodo_completo_when_janela_absent(self):
        fluxo = {
            "receita_recorrente": 100_000,
            "receita_total": 100_000,
            "despesa_total": 50_000,
            "despesa_mensal_media": 4_000,
        }
        r = RatiosCalculator().calculate(fluxo, _patrimonio())

        assert r.janela_referencia == "período completo"
        assert r.janela_n_meses == 0


class TestPlaceholders:
    """Sem passive_income/irpf, rentabilidade e alíquota IR são None (legacy_dict serializa "N/D")."""

    def test_rentabilidade_and_ir_default_none(self):
        r = RatiosCalculator().calculate(_fluxo_with_janela(), _patrimonio())

        assert r.rentabilidade_pct is None
        assert r.aliquota_efetiva_ir_pct is None

    def test_to_legacy_dict_renders_nd_when_none(self):
        r = RatiosCalculator().calculate(_fluxo_with_janela(), _patrimonio())
        d = r.to_legacy_dict()

        assert d["rentabilidade_pct"] == "N/D"
        assert d["aliquota_efetiva_ir_pct"] == "N/D"


class TestLegacyDict:
    def test_has_all_expected_fields(self):
        r = RatiosCalculator().calculate(_fluxo_with_janela(), _patrimonio())
        d = r.to_legacy_dict()

        required = {
            "taxa_poupanca_recorrente_pct",
            "taxa_poupanca_total_pct",
            "taxa_endividamento_pct",
            "autonomia_financeira_meses",
            "cobertura_despesas_meses",
            "rentabilidade_pct",
            "aliquota_efetiva_ir_pct",
            "janela_referencia",
            "janela_n_meses",
        }
        assert required.issubset(d.keys())


# ---------------------------------------------------------------------------
# A8.3 PR-A — wiring de passive_income / irpf
# ---------------------------------------------------------------------------


_DEFAULT_FONTES = {
    "dividendos": Decimal("10000"),
    "jcp": Decimal("0"),
    "aplicacoes": Decimal("0"),
    "ganho_capital": Decimal("0"),
    "exterior": Decimal("0"),
    "alugueis": Decimal("0"),
}


def make_passive_income(
    *, status: str = "ok", trs_pct: str = "2.50", ano: int | None = 2024
) -> PassiveIncomeResult:
    return PassiveIncomeResult(
        renda_passiva_anual_brl=Decimal("10000"),
        renda_passiva_mensal_brl=Decimal("833.33"),
        renda_passiva_por_fonte_brl=dict(_DEFAULT_FONTES),
        patrimonio_gerador_brl=Decimal("400000"),
        trs_efetiva_pct=Decimal(trs_pct),
        ano_referencia_irpf=ano,
        defasagem_meses=4,
        acumuladores_pct_gerador=Decimal("0"),
        status=status,  # type: ignore[arg-type]
    )


def _build_contribuinte_for_aliquota(ano_base: int) -> Contribuinte:
    return Contribuinte(
        cpf_masked="***.***.***-99",
        nome="Test",
        ano_base=ano_base,
        exercicio=ano_base + 1,
        modelo=ModeloDeclaracao.completo,
        natureza=NaturezaContribuinte.titular,
    )


def _build_pj_for_aliquota(renda: str, ir_pago: str) -> FontePagadoraPJ:
    return FontePagadoraPJ(
        cnpj="**.***.***/****-**",
        nome="ACME",
        rendimentos_tributaveis_brl=renda,
        contrib_previdenciaria_brl="0",
        ir_retido_brl=ir_pago,
    )


def make_irpf_for_aliquota(
    *, ano_base: int = 2024, renda: str = "100000.00", ir_pago: str = "15000.00"
) -> IRPFAnalyzer:
    decl = IRPFFullOutput(
        contribuinte=_build_contribuinte_for_aliquota(ano_base),
        rendimentos_pj=[_build_pj_for_aliquota(renda, ir_pago)],
        imposto_apurado=ImpostoApurado(
            base_calculo_brl=renda,
            ir_devido_brl=ir_pago,
            deducoes_totais_brl="0",
            ir_pago_brl=ir_pago,
        ),
        confidence=0.95,
    )
    return IRPFAnalyzer([decl])


class TestPassiveIncomeWiring:
    def test_rentabilidade_pct_populada_quando_status_ok(self):
        pi = make_passive_income(status="ok", trs_pct="3.25")
        r = RatiosCalculator().calculate(_fluxo_with_janela(), _patrimonio(), passive_income=pi)
        assert r.rentabilidade_pct == Decimal("3.25")

    def test_rentabilidade_none_quando_status_sem_irpf(self):
        pi = make_passive_income(status="sem_irpf", ano=None)
        r = RatiosCalculator().calculate(_fluxo_with_janela(), _patrimonio(), passive_income=pi)
        assert r.rentabilidade_pct is None

    def test_rentabilidade_none_quando_status_gerador_zero(self):
        pi = make_passive_income(status="gerador_zero")
        r = RatiosCalculator().calculate(_fluxo_with_janela(), _patrimonio(), passive_income=pi)
        assert r.rentabilidade_pct is None

    def test_to_legacy_dict_serializa_decimal_com_2_casas(self):
        pi = make_passive_income(status="ok", trs_pct="2.31")
        r = RatiosCalculator().calculate(_fluxo_with_janela(), _patrimonio(), passive_income=pi)
        d = r.to_legacy_dict()
        assert d["rentabilidade_pct"] == "2.31"


class TestIrpfAliquotaWiring:
    def test_aliquota_efetiva_calculada_com_irpf(self):
        # 15k IR / 100k renda = 15%
        irpf = make_irpf_for_aliquota(renda="100000", ir_pago="15000")
        r = RatiosCalculator().calculate(_fluxo_with_janela(), _patrimonio(), irpf=irpf)
        assert r.aliquota_efetiva_ir_pct == Decimal("15.00")

    def test_aliquota_zero_quando_ir_pago_zero(self):
        irpf = make_irpf_for_aliquota(renda="100000", ir_pago="0")
        r = RatiosCalculator().calculate(_fluxo_with_janela(), _patrimonio(), irpf=irpf)
        assert r.aliquota_efetiva_ir_pct == Decimal("0.00")

    def test_aliquota_none_quando_renda_zero(self):
        irpf = make_irpf_for_aliquota(renda="0", ir_pago="0")
        r = RatiosCalculator().calculate(_fluxo_with_janela(), _patrimonio(), irpf=irpf)
        assert r.aliquota_efetiva_ir_pct is None

    def test_aliquota_none_quando_irpf_omitido(self):
        r = RatiosCalculator().calculate(_fluxo_with_janela(), _patrimonio())
        assert r.aliquota_efetiva_ir_pct is None


class TestRegression:
    def test_callers_existentes_sem_kwargs_continuam_funcionando(self):
        # Garantia de back-compat: o legado chama calculate(fluxo, patrimonio)
        # sem nenhum dos novos kwargs. Deve devolver dataclass válida com
        # rentabilidade/aliquota=None e ``"N/D"`` no legacy_dict.
        r = RatiosCalculator().calculate(_fluxo_with_janela(), _patrimonio())
        d = r.to_legacy_dict()
        assert d["rentabilidade_pct"] == "N/D"
        assert d["aliquota_efetiva_ir_pct"] == "N/D"
        assert isinstance(r.taxa_poupanca_recorrente_pct, float)


# ---------------------------------------------------------------------------
# Track T06 / [[ADR-191]] §D3+D4 — Card Rentabilidade aninhado (4 status)
# ---------------------------------------------------------------------------


class TestRentabilidadeNestedRatio:
    """``FinancialRatios.rentabilidade`` aninhado cobre 4 status do enum."""

    def test_status_sem_irpf_quando_passive_income_sem_irpf(self):
        pi = make_passive_income(status="sem_irpf", ano=None)
        r = RatiosCalculator().calculate(
            _fluxo_with_janela(despesa_mensal_essencial=4000), _patrimonio(), passive_income=pi
        )
        assert r.rentabilidade is not None
        assert r.rentabilidade.status == "sem_irpf"
        assert r.rentabilidade.valor_pct is None
        assert r.rentabilidade.ano_base is None
        assert r.rentabilidade.defasagem_meses is None
        assert r.rentabilidade.cobertura_despesa_essencial_pct is None
        assert r.rentabilidade.meta_pct == Decimal("5.0")

    def test_status_gerador_zero_preserva_ano_base_e_defasagem(self):
        pi = make_passive_income(status="gerador_zero")
        r = RatiosCalculator().calculate(
            _fluxo_with_janela(despesa_mensal_essencial=4000), _patrimonio(), passive_income=pi
        )
        assert r.rentabilidade is not None
        assert r.rentabilidade.status == "gerador_zero"
        assert r.rentabilidade.valor_pct is None
        assert r.rentabilidade.ano_base == 2024
        assert r.rentabilidade.defasagem_meses == 4
        assert r.rentabilidade.cobertura_despesa_essencial_pct is None

    def test_status_sem_dados_essencial_quando_essencial_zero(self):
        # passive_income=ok mas window.despesa_mensal_essencial=0 → status flagado;
        # valor_pct ainda é exposto (UI mostra TRS, omite cobertura).
        pi = make_passive_income(status="ok", trs_pct="3.25")
        r = RatiosCalculator().calculate(
            _fluxo_with_janela(despesa_mensal_essencial=0), _patrimonio(), passive_income=pi
        )
        assert r.rentabilidade is not None
        assert r.rentabilidade.status == "sem_dados_essencial"
        assert r.rentabilidade.valor_pct == Decimal("3.25")
        assert r.rentabilidade.cobertura_despesa_essencial_pct is None

    def test_status_ok_calcula_cobertura(self):
        # renda_passiva_mensal=833.33 / essencial=4000 = 20.83%
        pi = make_passive_income(status="ok", trs_pct="3.25")
        r = RatiosCalculator().calculate(
            _fluxo_with_janela(despesa_mensal_essencial=4000), _patrimonio(), passive_income=pi
        )
        assert r.rentabilidade is not None
        assert r.rentabilidade.status == "ok"
        assert r.rentabilidade.valor_pct == Decimal("3.25")
        assert r.rentabilidade.cobertura_despesa_essencial_pct == Decimal("20.83")
        assert r.rentabilidade.ano_base == 2024
        assert r.rentabilidade.defasagem_meses == 4

    def test_meta_pct_pode_ser_customizada_via_config(self):
        pi = make_passive_income(status="sem_irpf", ano=None)
        calc = RatiosCalculator(RentabilidadeConfig(meta_pct=Decimal("4.0")))
        r = calc.calculate(
            _fluxo_with_janela(despesa_mensal_essencial=4000), _patrimonio(), passive_income=pi
        )
        assert r.rentabilidade is not None
        assert r.rentabilidade.meta_pct == Decimal("4.0")

    def test_rentabilidade_none_quando_passive_income_omitido(self):
        # Sem passive_income, o shape aninhado é None — UI render placeholder.
        r = RatiosCalculator().calculate(_fluxo_with_janela(), _patrimonio())
        assert r.rentabilidade is None

    def test_to_legacy_dict_serializa_rentabilidade_aninhado(self):
        pi = make_passive_income(status="ok", trs_pct="3.25")
        r = RatiosCalculator().calculate(
            _fluxo_with_janela(despesa_mensal_essencial=4000), _patrimonio(), passive_income=pi
        )
        d = r.to_legacy_dict()
        assert "rentabilidade" in d
        ren = d["rentabilidade"]
        assert ren is not None
        assert ren["status"] == "ok"
        assert ren["valor_pct"] == pytest.approx(3.25)
        assert ren["ano_base"] == 2024
        assert ren["defasagem_meses"] == 4
        assert ren["meta_pct"] == pytest.approx(5.0)
        assert ren["cobertura_despesa_essencial_pct"] == pytest.approx(20.83)
        # back-compat: campo flat preservado em paralelo.
        assert d["rentabilidade_pct"] == "3.25"

    def test_to_legacy_dict_serializa_none_quando_passive_income_omitido(self):
        r = RatiosCalculator().calculate(_fluxo_with_janela(), _patrimonio())
        d = r.to_legacy_dict()
        assert d["rentabilidade"] is None
        assert d["rentabilidade_pct"] == "N/D"


# ---------------------------------------------------------------------------
# A28.l2 — guardrail de sanidade determinístico (TRS > 8% a.a. → "suspeito")
# ---------------------------------------------------------------------------


class TestGuardrailTrsSuspeita:
    """Nunca publicar TRS aberrante silenciosa ([[ADR-191]] · A28.l2)."""

    def test_trs_acima_de_8_pct_flagra_suspeito(self):
        # Cenário dogfood 72883bde: 22,63% a.a. é impossível como yield.
        pi = make_passive_income(status="ok", trs_pct="22.63")
        r = RatiosCalculator().calculate(
            _fluxo_with_janela(despesa_mensal_essencial=4000), _patrimonio(), passive_income=pi
        )
        assert r.rentabilidade is not None
        assert r.rentabilidade.status == "suspeito"
        # valor permanece exposto — flagado, nunca silencioso.
        assert r.rentabilidade.valor_pct == Decimal("22.63")

    def test_suspeito_vence_sem_dados_essencial(self):
        pi = make_passive_income(status="ok", trs_pct="15.00")
        r = RatiosCalculator().calculate(
            _fluxo_with_janela(despesa_mensal_essencial=0), _patrimonio(), passive_income=pi
        )
        assert r.rentabilidade is not None
        assert r.rentabilidade.status == "suspeito"

    def test_trs_no_limiar_de_8_pct_permanece_ok(self):
        pi = make_passive_income(status="ok", trs_pct="8.00")
        r = RatiosCalculator().calculate(
            _fluxo_with_janela(despesa_mensal_essencial=4000), _patrimonio(), passive_income=pi
        )
        assert r.rentabilidade is not None
        assert r.rentabilidade.status == "ok"

    def test_threshold_customizavel_via_config(self):
        pi = make_passive_income(status="ok", trs_pct="6.00")
        calc = RatiosCalculator(RentabilidadeConfig(suspeito_threshold_pct=Decimal("5.0")))
        r = calc.calculate(
            _fluxo_with_janela(despesa_mensal_essencial=4000), _patrimonio(), passive_income=pi
        )
        assert r.rentabilidade is not None
        assert r.rentabilidade.status == "suspeito"

    def test_flat_rentabilidade_pct_deriva_da_trs_corrigida(self):
        # `rentabilidade_pct` continua alias da TRS ([[ADR-191]] §D2) — o
        # numerador/denominador corrigidos chegam via passive_income.
        pi = make_passive_income(status="ok", trs_pct="22.63")
        r = RatiosCalculator().calculate(
            _fluxo_with_janela(despesa_mensal_essencial=4000), _patrimonio(), passive_income=pi
        )
        assert r.rentabilidade_pct == Decimal("22.63")
        assert r.to_legacy_dict()["rentabilidade"]["status"] == "suspeito"
