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

# Exportação CSV do C6 Carbon — sem cabeçalho institucional, só dados transacionais.
# A combinação das colunas "Valor (em US$)" + "Cotação (em R$)" é exclusiva
# desse formato de exportação (cartão com transações internacionais em dólar).
C6_FATURA_CARBON_CSV = (
    "Data de Compra;Nome no Cartão;Final do Cartão;Categoria;Descrição;"
    "Parcela;Valor (em US$);Cotação (em R$);Valor (em R$)\n"
    "28/11/2025;DAVID ROBERT;5241;T&E;AIR EUROPA LINEAS AE;3/3;0;0;2747.60\n"
    "11/01/2026;DAVID ROBERT;5241;Serviços financeiros;BEYPAY*SAO PAULO;2/12;0;0;14.14\n"
    "15/01/2026;DAVID ROBERT;5241;Restaurantes;RESTAURANTE XYZ;;0;0;89.90\n"
)

BRADESCO_EXTRATO_POUPANCA = """
Banco Bradesco S.A.
Extrato Poupança
Ag: 1234 | Conta: 12345-6
Entre 01/02/2026 e 28/02/2026

SALDO ANTERIOR ................ 10.000,00
Rendimento .................... 50,00
SALDO ATUAL ................... 10.050,00
"""

# Exportação do Internet Banking Bradesco (screenshot/impressão da página web).
# "BRADESCO" e "Banco Bradesco S.A." NÃO aparecem nos primeiros 2000 chars —
# o nome da instituição só consta no rodapé (pos > 2000).
# Markers visíveis no preview: "Ágora Home Broker" na barra de navegação.
BRADESCO_EXTRATO_POUPANCA_WEB = (
    "Saldo disponível MARIANA\n"
    "Buscar Sair\n"
    "TERÇA-FEIRA, 31/03/2026 R$12.995,88 3221 • 77113-9 MIN\n"
    "Início Saldos e Extratos Pagamentos Pix Transferências Cartões "
    "Empréstimos Ágora Home Broker Investimentos Open Finance Imposto de Renda Mais opções\n"
    "Saldos e Extratos Conta-Poupança: Extrato Mensal / Por Período\n"
    "Data: Entre 01/09/2025 e 31/10/2025\n"
    "Contas: Ag: 3221 | CC: 77113-9\n"
    "Extrato de: Ag: 3221 | Conta: 77113-9\n"
    "Data Histórico Docto. Crédito (R$) Débito (R$) Saldo (R$)\n"
    "01/09/25 Rendimentos 0106731 97,28 38.459,58\n"
    "Poup Facil-depos a Partir 4/5/12\n"
    "30/09/25 tr Sal p/poup 3002372 3.954,66 46.906,52\n"
    "SALDO ANTERIOR 38.362,30\n"
)

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

# Extrato XLS exportado pelo Itaú Internet Banking.
# Não contém a palavra "EXTRATO" — cabeçalho é "Logotipo Itaú" + seção "Lançamentos"
# + títulos de coluna "lançamento ... saldos (R$)".
# Reproduz a estrutura real de pipe-separated rows gerada por _extract_file_preview.
ITAU_EXTRATO_CONTA_XLS = (
    "Logotipo Itaú |  |  |  | \n"
    "Atualização: | 08/04/2026 às 14:04:47 |  |  | \n"
    "Nome: | DAVID ROBERT CAMARGO DE CAMPOS |  |  | \n"
    "Agência: | 9652.0 |  |  | \n"
    "Conta: | 04397-8 |  |  | \n"
    " |  |  |  | \n"
    "Lançamentos |  |  |  | \n"
    " |  |  |  | \n"
    "data | lançamento | ag./origem | valor (R$) | saldos (R$)\n"
    "lançamentos |  |  |  | \n"
    "11/04/2025 | SALDO ANTERIOR |  |  | 48661.38\n"
    "22/04/2025 | PIX QRS WISE BRASIL |  | -591.8 | \n"
    "22/04/2025 | SALDO TOTAL DISPONÍVEL DIA |  |  | 48069.62\n"
)

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

    def test_c6bank_csv_format(self):
        """CSV de fatura Carbon não tem razão social — detectado pelas colunas USD+BRL."""
        assert detect_institution_by_content(C6_FATURA_CARBON_CSV) == "c6bank"

    def test_bradesco(self):
        assert detect_institution_by_content(BRADESCO_EXTRATO_POUPANCA) == "bradesco"

    def test_bradesco_web_ib_export(self):
        """IB Bradesco: 'Bradesco' só no rodapé (>2000 chars) — detectado via 'Ágora Home Broker'."""
        assert detect_institution_by_content(BRADESCO_EXTRATO_POUPANCA_WEB) == "bradesco"

    def test_itau(self):
        assert detect_institution_by_content(ITAU_EXTRATO_CONTA) == "itau"

    def test_itau_xls_format(self):
        """XLS do Itaú começa com 'Logotipo Itaú' — deve detectar itau."""
        assert detect_institution_by_content(ITAU_EXTRATO_CONTA_XLS) == "itau"

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

    def test_c6_carbon_csv(self):
        """CSV de exportação do Carbon (sem marcadores de PDF) deve detectar faturacarbon."""
        rule, req, sup = detect_type_by_content(C6_FATURA_CARBON_CSV)
        assert rule is not None
        assert rule.code == "faturacarbon"
        assert sup >= 1  # "Data de Compra" e "Final do Cartão" são supporting

    def test_bradesco_poupanca(self):
        rule, *_ = detect_type_by_content(BRADESCO_EXTRATO_POUPANCA)
        assert rule is not None
        # Poupança is more specific than generic extrato — should win
        assert rule.code == "extratopoupanca"

    def test_bradesco_poupanca_web_export(self):
        """Formato web do IB Bradesco: 'Conta-Poupança' no título → extratopoupanca."""
        rule, req, sup = detect_type_by_content(BRADESCO_EXTRATO_POUPANCA_WEB)
        assert rule is not None
        assert rule.code == "extratopoupanca"
        assert sup >= 1  # "SALDO ANTERIOR" é supporting

    def test_itau_extrato_conta(self):
        rule, *_ = detect_type_by_content(ITAU_EXTRATO_CONTA)
        assert rule is not None
        assert rule.code == "extratoconta"

    def test_itau_extrato_conta_xls(self):
        """XLS do Itaú não tem 'EXTRATO' — detectado via 'Logotipo Itaú' + colunas."""
        rule, req, sup = detect_type_by_content(ITAU_EXTRATO_CONTA_XLS)
        assert rule is not None
        assert rule.code == "extratoconta"
        assert sup >= 1  # "Atualização:" e "SALDO ANTERIOR" são supporting

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

    def test_high_confidence_c6_carbon_csv(self):
        """CSV de fatura Carbon sem razão social: confidence 1.0 (required + supporting)."""
        result = classify_text(C6_FATURA_CARBON_CSV)
        assert result.doc_type == "faturacarbon"
        assert result.institution == "c6bank"
        assert result.confidence == 1.0  # required (USD+BRL cols) + supporting (Data de Compra, Final do Cartão)

    def test_high_confidence_itau_xls(self):
        """XLS do Itaú sem 'EXTRATO': confidence 1.0 via Logotipo Itaú + Atualização."""
        result = classify_text(ITAU_EXTRATO_CONTA_XLS)
        assert result.doc_type == "extratoconta"
        assert result.institution == "itau"
        assert result.confidence == 1.0

    def test_high_confidence_bradesco_poupanca_web(self):
        """IB Bradesco web: institution via Ágora + type via Conta-Poupança → confidence 1.0."""
        result = classify_text(BRADESCO_EXTRATO_POUPANCA_WEB)
        assert result.doc_type == "extratopoupanca"
        assert result.institution == "bradesco"
        assert result.confidence == 1.0

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


# ---------------------------------------------------------------------------
# Fixtures — novos padrões adicionados para cobrir documentos reais
# ---------------------------------------------------------------------------

# CSV de exportação do Santander Unique: header exato "data,lançamento,valor" com BOM.
# Não contém nenhum marcador institucional explícito — o cabeçalho CSV é a âncora.
SANTANDER_FATURAUNIQUE_CSV = (
    "\ufeffdata,lançamento,valor\n"
    "2026-03-06,PAGAMENTO EFETUADO,-59\n"
    "2025-06-08,BRASIL PARAL*Bras 10/12,59\n"
    "2026-01-15,SQSP* DOMAIN#218016570,191.8\n"
)

# PDF de CDB do Santander (Internet Banking). "CDB DI SANTANDER" + "Central de Atendimento".
SANTANDER_CDB_PDF = (
    "Internet Banking\n"
    "DAVID ROBERT CAMARGO FERREIRA CAMPOS\n"
    "CDB DI SANTANDER\n"
    "Operação : 00331652260006541929\n"
    "Data da contratação : 30/08/2024\n"
    "Data de vencimento : 09/08/2028\n"
    "Rentabilidade : 100,00% do CDI\n"
    "Central de Atendimento Santander\n"
    "4004 - 3535 (Capitais e Regiões Metropolitanas)\n"
)

# XLS extrato do Santander: "EXTRATO DE CONTA CORRENTE" + "Conta: 1652-01.001341.6".
# "Seguro do limite da conta" está no rodapé (além dos 2000 chars do preview).
# A âncora primária é o formato de conta "NNNN-NN.NNNNNN.N".
SANTANDER_EXTRATO_XLS = (
    "EXTRATO DE CONTA CORRENTE \n"
    "DAVID ROBERT CAMARGO FERREIRA CAMPOS  |  | Conta: 1652-01.001341.6\n"
    "Tipo de Lancamento: Todos | Extrato de 08/01/2026 a 08/04/2026\n"
    "Data  | Descrição  | Docto  | Situação  | Crédito (R$)  | Débito (R$)  | Saldo (R$)\n"
    "06/04/2026  | JUROS SALDO UTILIZ ATE LIMITE PERIODO: 03/03 A 02/04/26 | -31,67 | 506,98\n"
    "06/04/2026  | PIX RECEBIDO DOUGLAS CAMARGO DE CAMPOS | 432371 | 100,00 | 538,65\n"
)

# XLSX de resumo de CDB Santander: "CDB DI SANTANDER" + "CDB PROG SANTANDER".
SANTANDER_CDB_RESUMO_XLSX = (
    "CDB | Valor Total: R$300.444,46 | Valores Referentes a: 08/04/2026\n"
    "CDB DI SANTANDER | Valor Total: R$137.857,68 | Disponível para Resgate: R$133.032,53\n"
    "Operação | Valor Total(R$): | Disponível para Resgate(R$):\n"
    "00331652260006380267 | R$137.857,68 | R$133.032,53\n"
    "CDB PROG SANTANDER | Valor Total: R$60.733,04 | Disponível para Resgate: R$58.854,76\n"
)

# PDF extrato da Rico Corretora: razão social completa no cabeçalho.
RICO_EXTRATO_PDF = (
    "29/03/2026 08:36 RICO CORRETORA DE TITULOS E VALORES MOBILIARIOS S.A. | Extrato\n"
    "Extrato da conta\n"
    "Data da consulta: 29/03/2026 08:36\n"
    "DAVID ROBERT CAMARGO DE CAMPOS  Conta: 6742394\n"
    "De: 30/09/2025  Até: 29/03/2026\n"
    "Saldo disponível: R$ 17.186,40\n"
    "Liq Mov Histórico Valor Saldo\n"
)

# PDF de fatura do QuintoAndar: cabeçalho usa o plural "Faturas de aluguel".
QUINTOANDAR_FATURA_PDF = (
    "Faturas de aluguel\n"
    "Praça Benedito Calixto, 186\n"
    "Janeiro Fevereiro Março\n"
    "Total de\n"
    "R$ 1.500,00\n"
    "QuintoAndar\n"
)

# CDB do C6 Bank via app (sem razão social completa, mas tem "C6 Invest").
C6_INVEST_CDB = (
    "Real R$ 6.930,11\n"
    "C6 Invest\n"
    "CDB C6 Pós-fixado Liq. Diária\n"
    "Renda Fixa\n"
    "102% do CDI\n"
    "CDB C6 Pós-fixado 3 meses\n"
    "103% do CDI\n"
)


class TestNewPatterns:
    """Testes para os padrões adicionados após auditoria dos 94 documentos."""

    def test_santander_faturaunique_csv_institution(self):
        """CSV Santander Unique: header 'data,lançamento,valor' com BOM → santander."""
        assert detect_institution_by_content(SANTANDER_FATURAUNIQUE_CSV) == "santander"

    def test_santander_faturaunique_csv_type(self):
        """CSV Santander Unique: deve classificar como faturaunique com conf=1.0."""
        result = classify_text(SANTANDER_FATURAUNIQUE_CSV)
        assert result.doc_type == "faturaunique"
        assert result.institution == "santander"
        assert result.confidence == 1.0

    def test_santander_faturaunique_csv_no_bom(self):
        """Sem BOM: o padrão ^\ufeff? deve continuar funcionando."""
        text_no_bom = SANTANDER_FATURAUNIQUE_CSV.lstrip("\ufeff")
        result = classify_text(text_no_bom)
        assert result.doc_type == "faturaunique"
        assert result.institution == "santander"

    def test_santander_cdb_pdf_institution(self):
        """'CDB DI SANTANDER' + 'Central de Atendimento Santander' → santander."""
        assert detect_institution_by_content(SANTANDER_CDB_PDF) == "santander"

    def test_santander_cdb_pdf_type(self):
        result = classify_text(SANTANDER_CDB_PDF)
        assert result.doc_type == "cdbdetalhes"
        assert result.institution == "santander"
        assert result.confidence >= 0.7

    def test_santander_extrato_xls_institution(self):
        """Extrato XLS Santander: 'Conta: 1652-01.001341.6' → santander."""
        assert detect_institution_by_content(SANTANDER_EXTRATO_XLS) == "santander"

    def test_santander_extrato_xls_type(self):
        result = classify_text(SANTANDER_EXTRATO_XLS)
        assert result.doc_type == "extratoconta"
        assert result.institution == "santander"

    def test_santander_cdb_resumo_xlsx(self):
        """XLSX de resumo CDB: 'CDB DI SANTANDER' → santander + cdbdetalhes."""
        result = classify_text(SANTANDER_CDB_RESUMO_XLSX)
        assert result.doc_type == "cdbdetalhes"
        assert result.institution == "santander"
        assert result.confidence >= 0.7

    def test_rico_extrato_pdf_institution(self):
        """'RICO CORRETORA DE TITULOS...' → rico."""
        assert detect_institution_by_content(RICO_EXTRATO_PDF) == "rico"

    def test_rico_extrato_pdf_full(self):
        result = classify_text(RICO_EXTRATO_PDF)
        assert result.institution == "rico"
        assert result.doc_type == "extratoconta"
        assert result.confidence >= 0.7

    def test_quintoandar_fatura_plural(self):
        """'Faturas de aluguel' (plural) deve classificar como faturaaluguel."""
        result = classify_text(QUINTOANDAR_FATURA_PDF)
        assert result.doc_type == "faturaaluguel"
        assert result.institution == "quintoandar"

    def test_c6_invest_institution(self):
        """'C6 Invest' no app → c6bank."""
        assert detect_institution_by_content(C6_INVEST_CDB) == "c6bank"

    def test_c6_invest_cdb_type(self):
        result = classify_text(C6_INVEST_CDB)
        assert result.doc_type == "cdbdetalhes"
        assert result.institution == "c6bank"


# ---------------------------------------------------------------------------
# Testes para novos padrões Caixa Econômica Federal
# ---------------------------------------------------------------------------

# Extrato da CEF com marcadores de rodapé de serviço (visíveis em PDFs com texto).
CAIXA_EXTRATO_FOOTER = """
Conta: 00012345-6
Período: 01/01/2026 a 31/03/2026

Lançamentos do dia  Data  Histórico  Valor  Saldo

Alô CAIXA 0800 726 0101
SAC CAIXA 0800 726 0207
"""

# Extrato da CEF com razão social completa (PDFs com texto de qualidade).
CAIXA_EXTRATO_RAZAOSOCIAL = """
CAIXA ECONÔMICA FEDERAL
Extrato por período
Período dos lançamentos: 01/01/2026 a 31/03/2026
SALDO ANTERIOR: R$ 15.234,56
"""

# Extrato da CEF — apenas "SAC CAIXA" no rodapé, sem razão social.
CAIXA_EXTRATO_SAC_ONLY = """
Conta: 987654321 Agência: 1234
Data      Histórico          Valor       Saldo
01/01/26  Depósito           1.000,00    5.000,00
15/01/26  Saque              -500,00     4.500,00
SAC CAIXA
"""

# Extrato Bradesco com "SAC - Alô Bradesco" no rodapé (além dos 2000 chars).
# Ágora Home Broker aparece no nav a ~170 chars — dentro do preview.
BRADESCO_IB_POUPANCA = (
    "Saldo disponível MARIANA\n"
    "Buscar Sair\n"
    "TERÇA-FEIRA, 31/03/2026 R$12.995,88 3221 • 77113-9 MIN\n"
    "Início Saldos e Extratos Pagamentos Pix Transferências Cartões "
    "Empréstimos Ágora Home Broker Investimentos Open Finance Imposto de Renda Mais opções\n"
    "Saldos e Extratos Conta-Poupança: Extrato (Últimos Lançamentos)\n"
    "Data Histórico Docto. Crédito (R$) Débito (R$) Saldo (R$)\n"
    "05/01/26 bx Aut Cta Cor* 0077113 - 1.673,05 27.551,59\n"
    "14/01/26 Rendimentos 1406708 29,44 27.361,03\n"
    "Poup Facil-depos a Partir 4/5/12\n"
    # simula o rodapé além dos 2000 chars
    "Fone Fácil\n"
    "SAC - Alô Bradesco\n"
    "0800 570 0022 0800 704 8383\n"
)


class TestCaixaPatterns:
    """Testes para os padrões novos da Caixa Econômica Federal."""

    def test_caixa_alo_caixa_institution(self):
        """'Alô CAIXA' no rodapé → caixa."""
        assert detect_institution_by_content(CAIXA_EXTRATO_FOOTER) == "caixa"

    def test_caixa_sac_caixa_institution(self):
        """'SAC CAIXA' sozinho → caixa."""
        assert detect_institution_by_content(CAIXA_EXTRATO_SAC_ONLY) == "caixa"

    def test_caixa_razaosocial_institution(self):
        """'CAIXA ECONÔMICA FEDERAL' → caixa."""
        assert detect_institution_by_content(CAIXA_EXTRATO_RAZAOSOCIAL) == "caixa"

    def test_caixa_extrato_footer_full_classification(self):
        """Extrato com rodapé 'Alô CAIXA' + 'Lançamentos do dia' → extratoconta."""
        result = classify_text(CAIXA_EXTRATO_FOOTER)
        assert result.institution == "caixa"
        assert result.doc_type == "extratoconta"
        assert result.confidence >= 0.7

    def test_caixa_extrato_razaosocial_full(self):
        """Extrato com razão social completa → extratoconta conf=1.0."""
        result = classify_text(CAIXA_EXTRATO_RAZAOSOCIAL)
        assert result.institution == "caixa"
        assert result.doc_type == "extratoconta"
        assert result.confidence == 1.0

    def test_bradesco_ib_poupanca_via_agora(self):
        """Extrato IB Bradesco com 'Ágora Home Broker' → bradesco + extratopoupanca."""
        result = classify_text(BRADESCO_IB_POUPANCA)
        assert result.institution == "bradesco"
        assert result.doc_type == "extratopoupanca"
        assert result.confidence >= 0.7

    def test_bradesco_sac_footer(self):
        """'SAC - Alô Bradesco' no rodapé → bradesco (via Fone Fácil pattern)."""
        footer_only = "Fone Fácil\nCapitais e regiões metropolitanas\n0800 570 0022\n"
        assert detect_institution_by_content(footer_only) == "bradesco"
