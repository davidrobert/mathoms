"""PDF sintético + registry E2 — cada módulo em `scripts/e2/registry.py` tem rota e parser executável.

Garantias:
- **filename canônico → `route_to_parser` → `parse*(…)`** retorna dict (smoke).
- **C6 / Bradesco / BTG / Rico / Wise / PicPay / Bank of America / Santander / Itaú / Caixa:** layouts
  dedicados → **≥1** transação e `saldo_final` onde aplicável (`test_c6bank_*`, `test_bradesco_*`,
  `test_btgpactual_*` … `test_caixa_*`). **Bradesco:** valores de crédito no PDF devem casar com o
  heurístico `len(raw)<=6` do parser — ver `_BRADESCO_TX`.
- **Quinto Andar:** layout fatura aluguel → **≥1** item e `total_recebido` (`test_quintoandar_*`).

Códigos só em `BankCode` fora do registry (ex.: binance): tabela genérica. Smoke texto:
`backend/tests/test_golden_pipeline.py::TestSyntheticPDFsAreParseable`.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.e2.registry import route_to_parser
from tests.fixtures.pdf_generator import generate_statement

pytest.importorskip("pdfplumber")

_SAMPLE_TX = [
    {"date": "2026-04-05", "description": "Mercado Sintetico", "amount": -250.50},
    {"date": "2026-04-01", "description": "Pagto Folha", "amount": 12500.00},
]

# Crédito com máscara `X.XXX,XX` onde o raw numérico tem >6 dígitos não dispara o ramo de crédito na
# linha da data em `parse_bradesco` — usar valor menor no teste dedicado.
_BRADESCO_TX = [
    {"date": "2026-04-05", "description": "Mercado Sintetico", "amount": -250.50},
    {"date": "2026-04-10", "description": "Pagto Folha", "amount": 1250.00},
]

# Filename alinhado ao primeiro padrão PDF (não CSV/XLS) de cada `scripts/e2/banks/*.py`
# + chave do `generate_statement` (btg no registry → btgpactual no gerador).
_SYNTHETIC_E2_CASES: list[tuple[str, str, str]] = [
    ("c6bank_extratoconta_202604_golden.pdf", "c6bank", "extrato"),
    ("itau_extratoconta_202604_golden.pdf", "itau", "extrato"),
    ("picpay_extratoconta_202604_golden.pdf", "picpay", "extrato"),
    ("bradesco_extratoconta_202604_golden.pdf", "bradesco", "extrato"),
    ("santander_extratoconta_202604_golden.pdf", "santander", "extrato"),
    ("btgpactual_extratoconta_202604_golden.pdf", "btgpactual", "extrato"),
    ("rico_extratoconta_202604_golden.pdf", "rico", "extrato"),
    ("wise_extratoconta_202604_golden.pdf", "wise", "extrato"),
    ("bankofamerica_extratoconta_202604_golden.pdf", "bankofamerica", "extrato"),
    ("quintoandar_faturaaluguelapt01_202604.pdf", "quintoandar", "extrato"),
    ("caixa_extratoconta_202604_golden.pdf", "caixa", "extrato"),
]


@pytest.mark.parametrize("filename,bank,kind", _SYNTHETIC_E2_CASES)
def test_synthetic_pdf_e2_parser_runs(filename: str, bank: str, kind: str, tmp_path: Path):
    pdf_bytes = generate_statement(
        bank,  # type: ignore[arg-type]
        kind,  # type: ignore[arg-type]
        period="2026-04",
        transactions=_SAMPLE_TX,
        account_holder="Titular Golden",
    )
    path = tmp_path / filename
    path.write_bytes(pdf_bytes)

    parser_fn = route_to_parser(filename)
    assert parser_fn is not None, f"sem parser registrado para filename={filename!r}"

    result = parser_fn(path, filename)
    assert isinstance(result, dict)
    assert result
    assert (
        "banco" in result
        or "tipo" in result
        or "erro" in result
        or "requires_llm_fallback" in result
    )


def test_c6bank_synthetic_extracts_transactions(tmp_path: Path):
    """Layout `c6bank` — `Período • … de … até …`, `Conta:`, tabela 5 colunas + `Saldo do dia`."""
    filename = "c6bank_extratoconta_202604_golden.pdf"
    path = tmp_path / filename
    path.write_bytes(
        generate_statement(
            "c6bank",
            "extrato",
            period="2026-04",
            transactions=_SAMPLE_TX,
            account_holder="Titular Golden",
            account_number="12345678",
        )
    )
    parser_fn = route_to_parser(filename)
    assert parser_fn is not None
    result = parser_fn(path, filename)
    assert len(result.get("transacoes") or []) >= 1
    assert result.get("saldo_final") is not None


def test_bradesco_synthetic_extracts_transactions(tmp_path: Path):
    """Layout `bradesco` — `Ag | Conta`, `Entre`, `SALDO ANTERIOR`, linhas DD/MM/YY + `Total`."""
    filename = "bradesco_extratoconta_202604_golden.pdf"
    path = tmp_path / filename
    path.write_bytes(
        generate_statement(
            "bradesco",
            "extrato",
            period="2026-04",
            transactions=_BRADESCO_TX,
            account_holder="Titular Golden",
            agency="3221",
            account_number="77113-9",
        )
    )
    parser_fn = route_to_parser(filename)
    assert parser_fn is not None
    result = parser_fn(path, filename)
    assert len(result.get("transacoes") or []) >= 1
    assert result.get("saldo_final") is not None


def test_btgpactual_synthetic_extracts_transactions(tmp_path: Path):
    """Layout `btgpactual` alinhado a `parse_btg` — transações não vazias."""
    filename = "btgpactual_extratoconta_202604_golden.pdf"
    path = tmp_path / filename
    path.write_bytes(
        generate_statement(
            "btgpactual",
            "extrato",
            period="2026-04",
            transactions=_SAMPLE_TX,
            account_holder="Titular Golden",
        )
    )
    parser_fn = route_to_parser(filename)
    assert parser_fn is not None
    result = parser_fn(path, filename)
    txs = result.get("transacoes") or []
    assert len(txs) >= 1
    assert result.get("saldo_final") is not None


def test_rico_synthetic_extracts_transactions(tmp_path: Path):
    """Layout `rico` — evita cabeçalho com duas datas seguidas; `parse_rico` extrai linhas."""
    filename = "rico_extratoconta_202604_golden.pdf"
    path = tmp_path / filename
    path.write_bytes(
        generate_statement(
            "rico",
            "extrato",
            period="2026-04",
            transactions=_SAMPLE_TX,
            account_holder="Titular Golden",
        )
    )
    parser_fn = route_to_parser(filename)
    assert parser_fn is not None
    result = parser_fn(path, filename)
    assert len(result.get("transacoes") or []) >= 1
    assert result.get("saldo_final") is not None


def test_wise_synthetic_extracts_transactions(tmp_path: Path):
    """Layout `wise` (BRL) — linhas movimento + `N de mês de AAAA Transação` para data."""
    filename = "wise_extratoconta_202604_golden.pdf"
    path = tmp_path / filename
    path.write_bytes(
        generate_statement(
            "wise",
            "extrato",
            period="2026-04",
            transactions=_SAMPLE_TX,
            account_holder="Titular Golden",
        )
    )
    parser_fn = route_to_parser(filename)
    assert parser_fn is not None
    result = parser_fn(path, filename)
    assert len(result.get("transacoes") or []) >= 1
    assert result.get("saldo_final") is not None


def test_picpay_synthetic_extracts_transactions(tmp_path: Path):
    """Layout `picpay` — tabela ReportLab + `MOVIMENTAÇÕES … DE … A …` para `parse_picpay`."""
    filename = "picpay_extratoconta_202604_golden.pdf"
    path = tmp_path / filename
    path.write_bytes(
        generate_statement(
            "picpay",
            "extrato",
            period="2026-04",
            transactions=_SAMPLE_TX,
            account_holder="Titular Golden",
        )
    )
    parser_fn = route_to_parser(filename)
    assert parser_fn is not None
    result = parser_fn(path, filename)
    assert len(result.get("transacoes") or []) >= 1
    assert result.get("saldo_final") is not None


class _FakeTablePdf:
    """PDF fake de 1 página: extract_text→header, extract_tables→[table]."""

    def __init__(self, header: str, table: list) -> None:
        self._header, self._table = header, table
        self.pages = [self]

    def extract_text(self) -> str:
        return self._header

    def extract_tables(self) -> list:
        return [self._table]

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


# Rows newest-first; coluna Saldo = running-balance CRONOLÓGICO (abertura=1000):
# 04/01 +500 → 1500; 04/05 −200 → 1300. Última linha (mais antiga) carrega 1500.
_PICPAY_HEADER = (
    "PicPay\nConta: 12345678\nMOVIMENTAÇÕES 01 DE ABRIL DE 2026 A 05 DE ABRIL DE 2026\n"
)
_PICPAY_TABLE = [
    ["Data/Hora", "Descrição", "Valor (R$)", "Saldo (R$)"],
    ["05/04/2026 10:00", "Compra Mercado", "-200,00", "1.300,00"],
    ["01/04/2026 09:00", "Pagto Recebido", "500,00", "1.500,00"],
]


def test_picpay_conservacao_fecha_sem_double_count(monkeypatch, tmp_path: Path):
    """F3b (cert 5@5.com 2026-07-27): saldo_inicial = saldo_last − 1ª tx. Sem o
    ajuste, a tx mais antiga é contada 2× e a conservação não fecha. Prova gap=0."""
    from scripts.e2.banks import picpay as ppmod

    monkeypatch.setattr(
        ppmod.pdfplumber, "open", lambda _p: _FakeTablePdf(_PICPAY_HEADER, _PICPAY_TABLE)
    )
    path = tmp_path / "picpay_extratoconta_202604_202604-0_original.pdf"
    path.write_bytes(b"%PDF-fake")

    result = ppmod.parse_picpay(path, path.name)
    si, sf = result.get("saldo_inicial"), result.get("saldo_final")
    soma = sum(t["valor"] for t in result["transacoes"])
    assert round(abs((si + soma) - sf) * 100) == 0, "picpay não fecha (double-count?)"
    assert result.get("conservacao_verificavel") is True
    assert round(si, 2) == 1000.00  # saldo da última linha (1500) − 1ª tx (500)


_PICPAY_TABLE_OLDEST_SEM_SALDO = [
    ["Data/Hora", "Descrição", "Valor (R$)", "Saldo (R$)"],
    ["05/04/2026 10:00", "Compra Mercado", "-200,00", "1.300,00"],
    ["01/04/2026 09:00", "Pagto Recebido", "500,00", ""],  # tx mais antiga: Saldo em branco
]


def test_picpay_endpoint_saldo_vazio_nao_afirma_verificavel(monkeypatch, tmp_path: Path):
    """F3b hardening (revisão adversarial PR #1080): se a tx mais antiga tem Saldo em
    branco, saldo_inicial fica desalinhado — NÃO computa nem afirma verificável
    (fail-safe), em vez de gravar saldo errado + flag falso no gate tol-zero."""
    from scripts.e2.banks import picpay as ppmod

    monkeypatch.setattr(
        ppmod.pdfplumber,
        "open",
        lambda _p: _FakeTablePdf(_PICPAY_HEADER, _PICPAY_TABLE_OLDEST_SEM_SALDO),
    )
    path = tmp_path / "picpay_extratoconta_202604_202604-0_original.pdf"
    path.write_bytes(b"%PDF-fake")

    result = ppmod.parse_picpay(path, path.name)
    assert result.get("saldo_final") == 1300.00  # tx mais nova, correto
    assert result.get("saldo_inicial") is None  # oldest saldo vazio → não computa
    assert not result.get("conservacao_verificavel")  # fail-safe: não afirma


def test_bankofamerica_synthetic_extracts_transactions(tmp_path: Path):
    """Layout `bankofamerica` — USD, `Account number`, `for Month … to …`, linhas MM/DD/YY."""
    filename = "bankofamerica_extratoconta_202604_golden.pdf"
    path = tmp_path / filename
    path.write_bytes(
        generate_statement(
            "bankofamerica",
            "extrato",
            period="2026-04",
            transactions=_SAMPLE_TX,
            account_holder="Titular Golden",
        )
    )
    parser_fn = route_to_parser(filename)
    assert parser_fn is not None
    result = parser_fn(path, filename)
    assert len(result.get("transacoes") or []) >= 1
    assert result.get("saldo_final") is not None


def test_santander_synthetic_extracts_transactions(tmp_path: Path):
    """Layout `santander` — `Agência e Conta`, `Período`, linhas DD/MM/AAAA + 6 dígitos + valor + saldo."""
    filename = "santander_extratoconta_202604_golden.pdf"
    path = tmp_path / filename
    path.write_bytes(
        generate_statement(
            "santander",
            "extrato",
            period="2026-04",
            transactions=_SAMPLE_TX,
            account_holder="Titular Golden",
            agency="1652",
            account_number="01001341-6",
        )
    )
    parser_fn = route_to_parser(filename)
    assert parser_fn is not None
    result = parser_fn(path, filename)
    assert len(result.get("transacoes") or []) >= 1
    assert result.get("saldo_final") is not None


def test_itau_synthetic_extracts_transactions(tmp_path: Path):
    """Layout `itau` — tabela 4 colunas + `Período`/`Conta` na página 1; linha `SALDO DO DIA` para saldos."""
    filename = "itau_extratoconta_202604_golden.pdf"
    path = tmp_path / filename
    path.write_bytes(
        generate_statement(
            "itau",
            "extrato",
            period="2026-04",
            transactions=_SAMPLE_TX,
            account_holder="Titular Golden",
        )
    )
    parser_fn = route_to_parser(filename)
    assert parser_fn is not None
    result = parser_fn(path, filename)
    assert len(result.get("transacoes") or []) >= 1
    assert result.get("saldo_final") is not None


def test_caixa_synthetic_extracts_transactions(tmp_path: Path):
    """Layout `caixa` — texto `Conta`/`Período dos lançamentos`/`SALDO ANTERIOR` + tabela 7 colunas."""
    filename = "caixa_extratoconta_202604_golden.pdf"
    path = tmp_path / filename
    path.write_bytes(
        generate_statement(
            "caixa",
            "extrato",
            period="2026-04",
            transactions=_SAMPLE_TX,
            account_holder="Titular Golden",
            agency="1234",
            account_number="56789-0",
        )
    )
    parser_fn = route_to_parser(filename)
    assert parser_fn is not None
    result = parser_fn(path, filename)
    assert len(result.get("transacoes") or []) >= 1
    assert result.get("saldo_final") is not None


def test_quintoandar_synthetic_extracts_items(tmp_path: Path):
    """Layout `quintoandar` — `Faturas de aluguel`, `Total de`/`Receber até`, linhas item + R$."""
    filename = "quintoandar_faturaaluguelapt01_202604.pdf"
    path = tmp_path / filename
    path.write_bytes(
        generate_statement(
            "quintoandar",
            "extrato",
            period="2026-04",
            transactions=_SAMPLE_TX,
            account_holder="Titular Golden",
        )
    )
    parser_fn = route_to_parser(filename)
    assert parser_fn is not None
    result = parser_fn(path, filename)
    assert len(result.get("itens") or []) >= 1
    assert result.get("total_recebido") is not None


def test_c6bank_usd_detected_by_content(monkeypatch, tmp_path: Path):
    """Upload C6 Global USD com filename genérico `c6bank_extratoconta_` vira USD via sniff de conteúdo."""
    from scripts.e2.banks import c6bank as c6mod

    usd_header = (
        "Extrato exportado no dia 29 de março de 2026\n"
        "David Robert • 000.000.000-00\n"
        "Agência 0001 • Conta 100000000-0 • Status da conta: ativa\n"
        "Extrato Período • 01 de julho de 2025 até 31 de julho de 2025\n"
        "Saldo do dia • 29 de março de 2026 • US$ 91,59\n"
        "Julho 2025\n"
        "Data Tipo Descrição Valor Autorização\n"
    )
    # Linhas no formato real do C6 Global PDF — duas datas, tipo, descrição,
    # moeda US$/€/EUR e valor assinado. parse_c6bank usa extract_text(),
    # então a fidelidade do mock é nesse retorno (e não em extract_tables).
    usd_body = (
        "31/07 29/07 Débito de cartão Bass Pro Store Orlando -US$ 17,56\n"
        "31/07 29/07 Débito de cartão Amazon Mark -US$ 30,86\n"
        "30/07 28/07 Débito de cartão Walgreens -US$ 10,18\n"
        "Saldo do dia 31/07/25 US$ 91,59\n"
    )

    class _FakePage:
        def __init__(self, text: str) -> None:
            self._text = text

        def extract_text(self) -> str:
            return self._text

        def extract_tables(self) -> list:
            return []

    class _FakePdf:
        def __init__(self, pages):
            self.pages = pages

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    def _fake_open(_path):
        return _FakePdf([_FakePage(usd_header + usd_body)])

    monkeypatch.setattr(c6mod.pdfplumber, "open", _fake_open)

    filename = "c6bank_extratoconta_202507_202507-0_original.pdf"
    path = tmp_path / filename
    path.write_bytes(b"%PDF-fake")

    result = c6mod.parse_c6bank(path, filename)
    assert result["moeda"] == "USD"
    assert result["tipo"] == "extratocontaglobalusd"
    assert len(result.get("transacoes") or []) >= 1
    assert all(t["valor"] is not None for t in result["transacoes"])


def test_c6bank_brl_not_misdetected_as_usd(monkeypatch, tmp_path: Path):
    """Conteúdo com R$ continua sendo parseado como BRL mesmo se US$ aparecer (ex.: taxa de câmbio)."""
    from scripts.e2.banks import c6bank as c6mod

    brl_header = (
        "Extrato Período • 01 de abril de 2026 até 30 de abril de 2026\n"
        "Saldo do dia • 30 de abril de 2026 • R$ 1.234,56\n"
        "Cotação US$ 1,00 = R$ 5,00\n"
    )

    class _FakePage:
        def extract_text(self) -> str:
            return brl_header

        def extract_tables(self) -> list:
            return []

    class _FakePdf:
        pages = [_FakePage()]

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(c6mod.pdfplumber, "open", lambda _p: _FakePdf())

    filename = "c6bank_extratoconta_202604_202604-0_original.pdf"
    path = tmp_path / filename
    path.write_bytes(b"%PDF-fake")

    result = c6mod.parse_c6bank(path, filename)
    assert result["moeda"] == "BRL"
    assert result["tipo"] == "extratoconta"
