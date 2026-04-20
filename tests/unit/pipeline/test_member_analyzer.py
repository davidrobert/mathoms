"""Tests — ``MemberAnalyzer`` (Sessão A3c · Fase 8 foundation).

Cobre paridade com helpers internos de ``scripts/e5_analyze.py:644-692``
(``_get_bens``, ``_imovel_valor``, ``_imovel_desc``, ``_veiculo_valor``,
``_investimento_valor``) + a fatia per-member de ``analyze_patrimonio``.
"""

from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.domain.services.member_analyzer import (  # noqa: E402
    MemberAnalyzer,
    MemberPatrimonio,
)


# =============================================================================
# Helpers
# =============================================================================


def _imovel(*, valor_irpf=None, valor_31_12=None, valor=None, descricao=None, endereco=None) -> dict:
    out: dict = {}
    if valor_31_12 is not None:
        out["valor_31_12_ano_base"] = valor_31_12
    if valor_irpf is not None:
        out["valor_irpf"] = valor_irpf
    if valor is not None:
        out["valor"] = valor
    if descricao is not None:
        out["descricao"] = descricao
    if endereco is not None:
        out["endereco"] = endereco
    return out


# =============================================================================
# Helpers individuais
# =============================================================================


class TestImovelValor:
    def test_prefers_valor_31_12_over_others(self):
        v = MemberAnalyzer.imovel_valor(_imovel(valor_31_12=500_000, valor_irpf=400_000, valor=300_000))
        assert v == Decimal("500000")

    def test_falls_back_to_valor_irpf(self):
        v = MemberAnalyzer.imovel_valor(_imovel(valor_irpf=400_000))
        assert v == Decimal("400000")

    def test_falls_back_to_valor(self):
        v = MemberAnalyzer.imovel_valor(_imovel(valor=300_000))
        assert v == Decimal("300000")

    def test_returns_zero_when_no_valor(self):
        assert MemberAnalyzer.imovel_valor({"descricao": "casa"}) == Decimal(0)

    def test_accepts_string_with_brl_comma(self):
        v = MemberAnalyzer.imovel_valor(_imovel(valor_irpf="1.234.567,89"))
        assert v == Decimal("1234567.89")


class TestImovelDescricao:
    def test_uses_descricao_field(self):
        assert MemberAnalyzer.imovel_descricao({"descricao": "Casa Vila Madalena"}) == "casa vila madalena"

    def test_falls_back_to_endereco(self):
        assert MemberAnalyzer.imovel_descricao({"endereco": "Rua X"}) == "rua x"

    def test_falls_back_to_dados_completos_imovel(self):
        d = {"dados_completos": {"imovel": "Apto Centro"}}
        assert MemberAnalyzer.imovel_descricao(d) == "apto centro"

    def test_empty_when_nothing_present(self):
        assert MemberAnalyzer.imovel_descricao({}) == ""

    def test_description_field_english(self):
        assert MemberAnalyzer.imovel_descricao({"description": "Beach House"}) == "beach house"


class TestVeiculoValor:
    def test_prefers_valor_31_12(self):
        assert MemberAnalyzer.veiculo_valor({"valor_31_12_ano_base": 50_000, "valor": 100_000}) == Decimal("50000")

    def test_returns_zero_when_no_field(self):
        assert MemberAnalyzer.veiculo_valor({"modelo": "Civic"}) == Decimal(0)


class TestInvestimentoValor:
    def test_dict_with_valor_31_12(self):
        assert MemberAnalyzer.investimento_valor({"valor_31_12_ano_base": 100_000}) == Decimal("100000")

    def test_dict_with_valor_only(self):
        assert MemberAnalyzer.investimento_valor({"valor": 5_000}) == Decimal("5000")

    def test_scalar_value(self):
        assert MemberAnalyzer.investimento_valor(2_500) == Decimal("2500")

    def test_dict_without_valor_returns_zero(self):
        assert MemberAnalyzer.investimento_valor({"tipo": "CDB"}) == Decimal(0)

    def test_string_with_brazilian_format(self):
        assert MemberAnalyzer.investimento_valor("1.000,50") == Decimal("1000.50")


class TestBensFor:
    def test_returns_nested_bens_when_present(self):
        bens = {"imoveis": [{}]}
        assert MemberAnalyzer.bens_for({"bens": bens}) is bens

    def test_returns_member_when_flat(self):
        member = {"imoveis": [{}], "veiculos": []}
        assert MemberAnalyzer.bens_for(member) is member


# =============================================================================
# analyze() — composição
# =============================================================================


class TestAnalyze:
    def test_classifies_residencia_by_keyword(self):
        member = {
            "imoveis": [
                _imovel(valor_irpf=800_000, descricao="Casa Vila Madalena"),
                _imovel(valor_irpf=400_000, descricao="Apto Centro"),
            ],
            "total_bens": 1_200_000,
        }

        mp = MemberAnalyzer().analyze(
            member, member_key="david", residencia_keyword="vila madalena"
        )

        assert mp.residencia == Decimal("800000")
        assert mp.imoveis_investimento == Decimal("400000")

    def test_no_keyword_means_all_in_investimento(self):
        member = {
            "imoveis": [_imovel(valor=500_000, descricao="Casa")],
        }

        mp = MemberAnalyzer().analyze(member, member_key="david")

        assert mp.residencia == Decimal(0)
        assert mp.imoveis_investimento == Decimal("500000")

    def test_supports_nested_bens(self):
        member = {
            "bens": {
                "imoveis": [_imovel(valor=300_000)],
                "veiculos": [{"valor": 60_000}],
            }
        }

        mp = MemberAnalyzer().analyze(member, member_key="ana")

        assert mp.imoveis_investimento == Decimal("300000")
        assert mp.veiculos == Decimal("60000")

    def test_aggregates_investimentos_and_contas(self):
        member = {
            "investimentos": [
                {"valor": 100_000},
                {"valor": 50_000},
            ],
            "contas_bancarias": [
                {"valor": 10_000},
                {"valor": 5_000},
            ],
            "saldo_corretora": 20_000,
            "moeda_estrangeira": 30_000,
            "outros": 5_000,
        }

        mp = MemberAnalyzer().analyze(member, member_key="x")

        assert mp.investimentos == Decimal("150000")
        assert mp.contas_bancarias_extras == Decimal("70000")  # 15k + 20k + 30k + 5k

    def test_contas_bancarias_as_scalar(self):
        member = {"contas_bancarias": 25_000}

        mp = MemberAnalyzer().analyze(member, member_key="x")

        assert mp.contas_bancarias_extras == Decimal("25000")

    def test_extracts_total_bens_and_dividas(self):
        member = {"total_bens": 1_500_000, "total_dividas": 200_000}

        mp = MemberAnalyzer().analyze(member, member_key="x")

        assert mp.total_bens_irpf == Decimal("1500000")
        assert mp.total_dividas == Decimal("200000")

    def test_falls_back_to_dividas_field_when_total_dividas_missing(self):
        member = {"dividas": 50_000}

        mp = MemberAnalyzer().analyze(member, member_key="x")

        assert mp.total_dividas == Decimal("50000")

    def test_handles_empty_member(self):
        mp = MemberAnalyzer().analyze({}, member_key="x")

        assert mp.total_bens_calculado == Decimal(0)
        assert mp.total_dividas == Decimal(0)

    def test_total_bens_calculado_sum(self):
        member = {
            "imoveis": [_imovel(valor=500_000, descricao="Casa Vila")],
            "veiculos": [{"valor": 50_000}],
            "investimentos": [{"valor": 100_000}],
        }

        mp = MemberAnalyzer().analyze(
            member, member_key="x", residencia_keyword="vila"
        )

        # 500k residência + 0 imov inv + 50k veículos + 100k investimentos = 650k
        assert mp.total_bens_calculado == Decimal("650000")


# =============================================================================
# aggregate() — soma cross-membro
# =============================================================================


class TestAggregate:
    def test_sums_components_across_members(self):
        analyzer = MemberAnalyzer()
        a = analyzer.analyze(
            {"imoveis": [_imovel(valor=300_000, descricao="Vila")]},
            member_key="david",
            residencia_keyword="vila",
        )
        b = analyzer.analyze(
            {"investimentos": [{"valor": 200_000}], "veiculos": [{"valor": 40_000}]},
            member_key="mariana",
        )

        agg = analyzer.aggregate([a, b])

        assert agg["residencia"] == Decimal("300000")
        assert agg["imoveis_investimento"] == Decimal(0)
        assert agg["investimentos"] == Decimal("200000")
        assert agg["veiculos"] == Decimal("40000")

    def test_aggregate_empty_returns_zeros(self):
        agg = MemberAnalyzer().aggregate([])

        assert all(v == Decimal(0) for v in agg.values())


# =============================================================================
# to_legacy_floats
# =============================================================================


class TestLegacyFloats:
    def test_serializes_to_float_dict(self):
        mp = MemberPatrimonio(
            member_key="david",
            residencia=Decimal("800000"),
            imoveis_investimento=Decimal("400000"),
            veiculos=Decimal("60000"),
            investimentos=Decimal("150000"),
            contas_bancarias_extras=Decimal("25000"),
            total_bens_irpf=Decimal("1435000"),
            total_dividas=Decimal("100000"),
        )

        out = mp.to_legacy_floats()

        assert out["residencia"] == 800000.0
        assert isinstance(out["residencia"], float)
        assert out["member_key"] == "david"
