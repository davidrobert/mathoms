"""Regressão do defeito de escala ×100 em valor monetário string (r5/M28)."""

# Incidente: `consolidate_baseline.safe_float("243285.37")` devolvia 24328537.0 —
# strip incondicional do `.` como separador de milhar sobre string que já é decimal
# ISO. Propagou para `investimentos_consolidados.valores_31_12` e inflou 4 dos 6 KPIs
# do hero: patrimônio líquido, IF (798% contra 16,7% real), prazo de IF e o gap.
#
# O corpus real traz as DUAS convenções — o produtor interno emite ISO
# ("243285.37") e documento/LLM emite pt-BR ("243.285,37"). Parser que assume uma
# delas erra a outra por 100×, ou devolve 0 e o dinheiro desaparece.

from decimal import Decimal

import pytest

from pipeline.domain.services.money_parsing import (
    parse_taxa_ou_cotacao,
    parse_valor_monetario,
    valor_monetario_float,
)

# (entrada, esperado). Os 3 primeiros são os pares medidos no corpus de dogfood
# que provaram o ×100: dígitos idênticos com a vírgula deslocada duas casas.
FORMAS_REAIS = [
    ("243285.37", Decimal("243285.37")),
    ("243.285,37", Decimal("243285.37")),
    ("29000000.00", Decimal("29000000.00")),
    ("290000.00", Decimal("290000.00")),
    ("52303.69", Decimal("52303.69")),
    ("1234.56", Decimal("1234.56")),
    ("1.234,56", Decimal("1234.56")),
    ("R$ 1.234,56", Decimal("1234.56")),
    ("R$ 1234.56", Decimal("1234.56")),
    ("0.00", Decimal("0")),
    ("1.234.567,89", Decimal("1234567.89")),
    # pt-BR SEM vírgula — o agrupador é a única pista. Regrediu na 1ª passagem do
    # fix (`extract_if_meta_from_text("R$ 5.000.000")` devolvia 0,0).
    ("5.000.000", Decimal("5000000")),
    ("5.000", Decimal("5000")),
    ("R$ 5.000.000", Decimal("5000000")),
    # US/EU — o corpus tem USD (Bank of America, Wise) e EUR (C6 global, Wise).
    # `US$ 2,605.00` é literalmente o valor que aparece no render deste run.
    ("1,234.56", Decimal("1234.56")),
    ("1,234,567.89", Decimal("1234567.89")),
    ("US$ 2,605.00", Decimal("2605.00")),
    ("$2,605.00", Decimal("2605.00")),
    ("-1,234.56", Decimal("-1234.56")),
    ("€1.234,56", Decimal("1234.56")),
    ("€ 1,234.56", Decimal("1234.56")),
    ("EUR 987,65", Decimal("987.65")),
    ("USD 987.65", Decimal("987.65")),
    ("0,99", Decimal("0.99")),
]


@pytest.mark.parametrize("raw,esperado", FORMAS_REAIS)
def test_parse_aceita_iso_e_pt_br(raw, esperado):
    assert parse_valor_monetario(raw) == esperado


def test_iso_com_duas_decimais_nao_e_inflado_100x():
    """O caso exato do incidente — dígitos de 243285.37 não podem virar 24328537."""
    assert parse_valor_monetario("243285.37") == Decimal("243285.37")
    assert parse_valor_monetario("243285.37") != Decimal("24328537")


def test_pt_br_nao_colapsa_em_zero():
    """Falha-espelho: `patrimonio_types.safe_float` devolvia 0,00 e o dinheiro sumia."""
    assert parse_valor_monetario("243.285,37") == Decimal("243285.37")
    assert parse_valor_monetario("243.285,37") != Decimal(0)


@pytest.mark.parametrize("raw", [None, "", "   ", "N/D", "nan", "abc", "R$"])
def test_ausencia_devolve_none_nao_zero(raw):
    """Ausência ≠ zero medido. Zero coerced foi o que fabricou KPI falso."""
    assert parse_valor_monetario(raw) is None


def test_ultimo_separador_e_o_decimal():
    """Regra única que dispensa saber o locale: o último separador é o decimal."""
    assert parse_valor_monetario("1.234,56") == Decimal("1234.56")  # pt-BR
    assert parse_valor_monetario("1,234.56") == Decimal("1234.56")  # US/EU
    assert parse_valor_monetario("1.234.567,89") == parse_valor_monetario("1,234,567.89")


def test_agrupador_de_3_digitos_nao_e_lido_como_decimal():
    """`"5.000"` é cinco mil, não cinco. `"243285.37"` é decimal, não 24 milhões."""
    assert parse_valor_monetario("5.000") == Decimal("5000")
    assert parse_valor_monetario("243285.37") == Decimal("243285.37")


@pytest.mark.parametrize(
    "raw,esperado",
    [("0.025", "0.025"), ("0.001", "0.001"), ("0.500", "0.500"), ("-0.750", "-0.750")],
)
def test_zero_a_esquerda_nunca_e_agrupador(raw, esperado):
    # `protecao_patrimonial.pct_renda_anual` tem contrato `^-?\d+(\.\d{1,6})?$` e
    # domínio 0..1 (ADR-240) — sem esta guarda virava 1000×.
    """Grupo de milhar não tem zero líder: `"0.025"` é 25 milésimos, não 25."""
    assert parse_valor_monetario(raw) == Decimal(esperado)


class TestTaxaOuCotacao:
    """Taxa/cotação/σ têm 3+ decimais legítimos — agrupamento NUNCA se aplica."""

    @pytest.mark.parametrize(
        "raw,esperado",
        [
            ("5,432", "5.432"),  # cotação USD/BRL — `parse_brl` devolvia 5432
            ("5.4321", "5.4321"),  # PTAX escala 4
            ("22.000", "22.000"),  # σ 22% a.a. em Numeric(6,3) — money leria 22000
            ("0,995", "0.995"),
            ("0.025", "0.025"),
            ("6", "6"),
        ],
    )
    def test_virgula_e_sempre_decimal(self, raw, esperado):
        assert parse_taxa_ou_cotacao(raw) == Decimal(esperado)

    def test_divergencia_deliberada_vs_parser_monetario(self):
        """O mesmo texto tem leitura diferente por domínio — e isso é correto."""
        assert parse_valor_monetario("22.000") == Decimal("22000")  # vinte e dois mil
        assert parse_taxa_ou_cotacao("22.000") == Decimal("22.000")  # vinte e dois por cento

    @pytest.mark.parametrize("raw", [None, "", "N/D"])
    def test_ausencia_devolve_none(self, raw):
        assert parse_taxa_ou_cotacao(raw) is None


def test_numerico_passa_intacto():
    assert parse_valor_monetario(243285.37) == Decimal("243285.37")
    assert parse_valor_monetario(0) == Decimal(0)
    assert parse_valor_monetario(Decimal("1.5")) == Decimal("1.5")


def test_negativo_preservado():
    """Dívida chega negativa e o sinal é semântico (`is_divida` no consolidador)."""
    assert parse_valor_monetario("-1.234,56") == Decimal("-1234.56")
    assert parse_valor_monetario("-1234.56") == Decimal("-1234.56")


def test_float_shim_preserva_contrato_dos_call_sites():
    """Call-sites legados esperam float com default; o shim não reintroduz o bug."""
    assert valor_monetario_float("243285.37") == pytest.approx(243285.37)
    assert valor_monetario_float("243.285,37") == pytest.approx(243285.37)
    assert valor_monetario_float(None) == 0.0
    assert valor_monetario_float("lixo", default=-1.0) == -1.0


def test_nao_usa_float_no_caminho_de_parse():
    """ADR-090: dinheiro não transita por float durante o parse (erro de binário)."""
    assert parse_valor_monetario("0.1") + parse_valor_monetario("0.2") == Decimal("0.3")


# Antes do fix: 4 inflavam ISO em 100× e 1 devolvia 0 em pt-BR — 9 implementações,
# 6 comportamentos, para o mesmo conceito de domínio.
class TestParidadeEntreParsers:
    """Todos os parsers monetários do pipeline concordam nas duas convenções."""

    @staticmethod
    def _parsers():
        from pipeline.domain.services.e5_member_resolver import _safe_float as mr
        from pipeline.domain.services.endividamento_analyzer import _safe_float as en
        from pipeline.domain.services.if_projector import _safe_float as ifp
        from pipeline.domain.services.member_analyzer import _safe_decimal as ma
        from pipeline.domain.services.patrimonio_types import safe_float as pt
        from scripts.consolidate_baseline import safe_float as cb

        return {
            "consolidate_baseline.safe_float": cb,
            "e5_member_resolver._safe_float": mr,
            "endividamento_analyzer._safe_float": en,
            "if_projector._safe_float": ifp,
            "member_analyzer._safe_decimal": ma,
            "patrimonio_types.safe_float": pt,
        }

    @pytest.mark.parametrize("raw,esperado", [("243285.37", 243285.37), ("243.285,37", 243285.37)])
    def test_todos_concordam(self, raw, esperado):
        divergentes = {
            nome: float(fn(raw))
            for nome, fn in self._parsers().items()
            if abs(float(fn(raw)) - esperado) > 0.01
        }
        assert not divergentes, f"parsers divergem em {raw!r}: {divergentes}"
