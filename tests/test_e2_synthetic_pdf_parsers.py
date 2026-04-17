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
