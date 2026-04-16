"""Unit tests for the content-based document classifier."""

from __future__ import annotations

from pathlib import Path

import pytest

from backend.app.services.content_classifier import (
    classify_file,
    classify_text,
    detect_institution_by_content,
    detect_type_by_content,
    extract_period_from_content,
)


# ---------------------------------------------------------------------------
# Realistic content fixtures — based on actual bank export headers
# (see scripts/e2/banks/*.py for the parsers that confirm these markers)
# ---------------------------------------------------------------------------

SANTANDER_FATURA_UNIQUE = """
BANCO SANTANDER S.A.
CARTÃO SANTANDER UNIQUE - Final 1234

Vencimento da Fatura: 06/03/2026
Total a Pagar: R$ 4.532,18
Limite de Crédito: R$ 20.000,00
Pagamento Mínimo: R$ 452,00

Lançamentos:
01/02/2026 - SUPERMERCADO XPTO ............ R$ 234,00
"""

# Elite / Free / básico — sem marca "Unique"; muitos PDFs não repetem "FATURA" no topo.
SANTANDER_FATURA_ELITE = """
BANCO SANTANDER S.A.
Cartão de Crédito Santander Elite Mastercard — final 5678

Data de vencimento 18/03/2026
Total a pagar R$ 1.892,33
Pagamento mínimo R$ 189,23
Limite de crédito R$ 8.000,00

Lançamentos do período
"""

C6_FATURA_CARBON = """
C6 Bank S.A.
C6 Carbon Final 5678
C6 Carbon Virtual

Vencimento da Fatura: 05/03/2026
Total desta Fatura: R$ 1.200,00
Subtotal deste cartão: R$ 1.200,00
"""

BRADESCO_EXTRATO_POUPANCA = """
Banco Bradesco S.A.
Extrato Poupança
Ag: 1234 | Conta: 12345-6
Entre 01/02/2026 e 28/02/2026

SALDO ANTERIOR ................ 10.000,00
Rendimento .................... 50,00
SALDO ATUAL ................... 10.050,00
"""

ITAU_EXTRATO_CONTA = """
ITAU UNIBANCO S.A.
EXTRATO DE CONTA CORRENTE

Agência: 1234  Conta: 56789-0
Período: 01/01/2026 a 31/01/2026

SALDO ANTERIOR           R$ 5.000,00
01/01/2026 - Depósito    R$ 500,00
SALDO DO DIA             R$ 5.500,00
SALDO TOTAL DISPONÍVEL DIA 5.500,00
"""

BTG_POSICAO_INVESTIMENTOS = """
BTG Pactual
Posição Consolidada de Investimentos
Data: 31/03/2026

Renda Fixa: R$ 150.000,00
CDB: R$ 80.000,00  Rentabilidade 110% CDI  Vencimento 15/06/2027
Fundos de Investimento: R$ 45.000,00
Saldo Total: R$ 275.000,00
"""

C6_CDB_RESUMO = """
C6 Bank
CDB - Certificado de Depósito Bancário
Valor Total: R$ 50.000,00
Rentabilidade: 105% do CDI
Vencimento: 20/12/2027
Disponível para Resgate: R$ 52.130,00
"""

IRPF_INFORME_RENDIMENTOS = """
Banco Bradesco S.A.
Informe de Rendimentos Financeiros
Ano-Calendário 2025

Fonte Pagadora: BCO BRADESCO S.A.
Rendimentos Tributáveis: R$ 12.000,00
Isentos e Não Tributáveis: R$ 450,00
"""

BANKOFAMERICA_STATEMENT = """
Bank of America
Account Statement

Account number: 1234 5678 9012
Statement period: January 1, 2026 to January 31, 2026

Beginning balance: $5,000.00
Ending balance:    $5,234.56
Transaction detail:
  01/05/2026  Deposit   +$500.00
"""

IRREGULAR_DOC = "Este é um arquivo qualquer sem marcadores bancários."


class TestInstitutionDetection:
    def test_santander(self):
        assert detect_institution_by_content(SANTANDER_FATURA_UNIQUE) == "santander"

    def test_c6bank(self):
        assert detect_institution_by_content(C6_FATURA_CARBON) == "c6bank"

    def test_bradesco(self):
        assert detect_institution_by_content(BRADESCO_EXTRATO_POUPANCA) == "bradesco"

    def test_itau(self):
        assert detect_institution_by_content(ITAU_EXTRATO_CONTA) == "itau"

    def test_btg(self):
        assert detect_institution_by_content(BTG_POSICAO_INVESTIMENTOS) == "btgpactual"

    def test_bankofamerica(self):
        assert detect_institution_by_content(BANKOFAMERICA_STATEMENT) == "bankofamerica"

    def test_unknown_returns_none(self):
        assert detect_institution_by_content(IRREGULAR_DOC) is None


class TestTypeDetection:
    def test_santander_fatura(self):
        rule, req, sup = detect_type_by_content(SANTANDER_FATURA_UNIQUE)
        assert rule is not None
        assert rule.code == "faturaunique"
        assert sup >= 1

    def test_santander_fatura_elite_non_unique(self):
        rule, req, sup = detect_type_by_content(SANTANDER_FATURA_ELITE)
        assert rule is not None
        assert rule.code == "faturasantander"
        assert sup >= 1

    def test_c6_carbon(self):
        rule, *_ = detect_type_by_content(C6_FATURA_CARBON)
        assert rule is not None
        assert rule.code == "faturacarbon"

    def test_bradesco_poupanca(self):
        rule, *_ = detect_type_by_content(BRADESCO_EXTRATO_POUPANCA)
        assert rule is not None
        # Poupança is more specific than generic extrato — should win
        assert rule.code == "extratopoupanca"

    def test_itau_extrato_conta(self):
        rule, *_ = detect_type_by_content(ITAU_EXTRATO_CONTA)
        assert rule is not None
        assert rule.code == "extratoconta"

    def test_btg_posicao(self):
        rule, *_ = detect_type_by_content(BTG_POSICAO_INVESTIMENTOS)
        assert rule is not None
        # Posição consolidada is more specific than CDB even though CDB appears
        assert rule.code == "investimentosposicao"

    def test_c6_cdb(self):
        rule, *_ = detect_type_by_content(C6_CDB_RESUMO)
        assert rule is not None
        assert rule.code == "cdbdetalhes"

    def test_informe_rendimentos(self):
        rule, *_ = detect_type_by_content(IRPF_INFORME_RENDIMENTOS)
        assert rule is not None
        assert rule.code == "informerendimentos"

    def test_bankofamerica_statement(self):
        rule, *_ = detect_type_by_content(BANKOFAMERICA_STATEMENT)
        assert rule is not None
        assert rule.code == "extratocontausd"

    def test_irregular_returns_none(self):
        rule, req, sup = detect_type_by_content(IRREGULAR_DOC)
        assert rule is None


class TestPeriodExtraction:
    def test_date_range(self):
        assert (
            extract_period_from_content("Período: 01/01/2026 a 31/01/2026")
            == "202601_202601"
        )

    def test_month_year_br(self):
        assert extract_period_from_content("Fatura de março/2026") == "202603"

    def test_yyyymm_dash(self):
        assert extract_period_from_content("Extrato 2026-03") == "202603"

    def test_year_only(self):
        # "January 1, 2026" has no YYYYMM-compatible match — falls back to year
        assert extract_period_from_content("Reference year 2026") == "2026"

    def test_empty_returns_none(self):
        assert extract_period_from_content("") is None


class TestClassifyText:
    def test_high_confidence_santander(self):
        result = classify_text(SANTANDER_FATURA_UNIQUE)
        assert result.doc_type == "faturaunique"
        assert result.institution == "santander"
        assert result.confidence == 1.0
        assert result.period is not None

    def test_santander_elite_classifies_as_fatura(self):
        result = classify_text(SANTANDER_FATURA_ELITE)
        assert result.doc_type == "faturasantander"
        assert result.institution == "santander"
        assert result.confidence >= 0.85

    def test_high_confidence_c6_carbon(self):
        result = classify_text(C6_FATURA_CARBON)
        assert result.doc_type == "faturacarbon"
        assert result.institution == "c6bank"
        assert result.confidence >= 0.85

    def test_empty_text(self):
        result = classify_text("")
        assert result.doc_type is None
        assert result.confidence == 0.0

    def test_irregular_content(self):
        result = classify_text(IRREGULAR_DOC)
        assert result.doc_type is None
        assert result.institution is None

    def test_to_dict_shape(self):
        result = classify_text(BRADESCO_EXTRATO_POUPANCA)
        d = result.to_dict()
        assert set(d.keys()) >= {
            "institution", "doc_type", "dest_group", "period",
            "confidence", "source",
        }


class TestClassifyFileWithInjectedExtractor:
    """classify_file accepts a preview_extractor — perfect for stubbing."""

    def test_happy_path(self, tmp_path):
        f = tmp_path / "whatever_name.pdf"
        f.write_text("dummy")

        def fake_extractor(_path: Path) -> str:
            return ITAU_EXTRATO_CONTA

        result = classify_file(f, fake_extractor)
        assert result.doc_type == "extratoconta"
        assert result.institution == "itau"

    def test_filename_is_ignored(self, tmp_path):
        """A file NAMED like an extrato but CONTAINING a fatura → fatura wins."""
        f = tmp_path / "santander_extratoconta_202603-0_original.pdf"
        f.write_text("dummy")

        def fake_extractor(_path: Path) -> str:
            return SANTANDER_FATURA_UNIQUE

        result = classify_file(f, fake_extractor)
        assert result.doc_type == "faturaunique"  # content wins over filename

    def test_extractor_exception_returns_zero_confidence(self, tmp_path):
        f = tmp_path / "x.pdf"
        f.write_text("dummy")

        def bad_extractor(_path: Path) -> str:
            raise RuntimeError("boom")

        result = classify_file(f, bad_extractor)
        assert result.confidence == 0.0
        assert result.doc_type is None
        assert "preview_error" in result.source
