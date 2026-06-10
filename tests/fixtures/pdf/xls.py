"""Geradores de XLS binário sintético (xlwt, dev-dep) — paridade com ``parse_itau_xls`` e ``parse_santander_xls`` (A24.l7, corpus do flip strict)."""

from __future__ import annotations

from io import BytesIO

from tests.fixtures.pdf.formatters import format_brl, iso_date_to_br

Transaction = dict
_SALDO_INICIAL = 1000.0


def _save_xls(wb) -> bytes:
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _sorted_txs(transactions: list[Transaction]) -> list[Transaction]:
    return sorted(transactions, key=lambda t: str(t.get("date", "")))


def _write_itau_rows(sh, period: str, transactions: list[Transaction]) -> None:
    """Rows da row 10 nas colunas data=0/desc=1/valor=3/saldo=4 (defaults de ITAU_XLS_LAYOUT)."""
    yy, mm = period.split("-")
    row = 10
    sh.write(row, 0, f"01/{mm}/{yy}")
    sh.write(row, 1, "SALDO ANTERIOR")
    sh.write(row, 4, _SALDO_INICIAL)
    running = _SALDO_INICIAL
    for row, tx in enumerate(_sorted_txs(transactions), start=row + 1):
        amt = float(tx.get("amount", 0))
        running += amt
        sh.write(row, 0, iso_date_to_br(str(tx.get("date", f"{period}-01"))))
        sh.write(row, 1, str(tx.get("description", "Lancamento"))[:50])
        sh.write(row, 3, amt)
        sh.write(row, 4, running)
    sh.write(row + 1, 0, f"30/{mm}/{yy}")
    sh.write(row + 1, 1, "SALDO TOTAL DISPONÍVEL DIA")
    sh.write(row + 1, 4, running)


def generate_itau_xls(
    period: str,
    transactions: list[Transaction],
    *,
    account_holder: str = "Founder Teste",
    agency: str = "0001",
    account_number: str = "12345-6",
) -> bytes:
    """Sheet 'Lançamentos': header em (2,1)/(3,1)/(4,1) + rows via ``_write_itau_rows``."""
    import xlwt

    wb = xlwt.Workbook()
    sh = wb.add_sheet("Lançamentos")
    sh.write(2, 1, account_holder)
    sh.write(3, 1, agency)
    sh.write(4, 1, account_number)
    _write_itau_rows(sh, period, transactions)
    return _save_xls(wb)


def _write_santander_rows(sh, period: str, transactions: list[Transaction]) -> None:
    """Rows da row 6 nas colunas data=0/desc=1/credito=4/debito=5/saldo=6, valores string BRL (defaults de SANTANDER_XLS_LAYOUT)."""
    yy, mm = period.split("-")
    row = 6
    sh.write(row, 0, f"01/{mm}/{yy}")
    sh.write(row, 1, "SALDO ANTERIOR")
    sh.write(row, 6, format_brl(_SALDO_INICIAL))
    running = _SALDO_INICIAL
    for row, tx in enumerate(_sorted_txs(transactions), start=row + 1):
        amt = float(tx.get("amount", 0))
        running += amt
        sh.write(row, 0, iso_date_to_br(str(tx.get("date", f"{period}-01"))))
        sh.write(row, 1, str(tx.get("description", "Lancamento"))[:50])
        sh.write(row, 4 if amt >= 0 else 5, format_brl(abs(amt)))
        sh.write(row, 6, format_brl(running))
    sh.write(row + 1, 0, "TOTAL")


def generate_santander_xls(
    period: str,
    transactions: list[Transaction],
    *,
    account_holder: str = "Founder Teste",
) -> bytes:
    """Sheet única: titular em (2,0), conta em (2,4), período em (4,4) + rows via ``_write_santander_rows``."""
    import xlwt

    yy, mm = period.split("-")
    wb = xlwt.Workbook()
    sh = wb.add_sheet("Plan1")
    sh.write(2, 0, account_holder)
    sh.write(2, 4, "Conta: 1652-01.001341.6")
    sh.write(4, 4, f"Extrato de 01/{mm}/{yy} a 30/{mm}/{yy}")
    _write_santander_rows(sh, period, transactions)
    return _save_xls(wb)
