"""Geradores de XLS binário sintético (xlwt, dev-dep) — paridade com ``parse_itau_xls`` e ``parse_santander_xls`` (A24.l7, corpus do flip strict)."""

from __future__ import annotations

from io import BytesIO

from tests.fixtures.pdf.formatters import format_brl, iso_date_to_br

Transaction = dict


def generate_itau_xls(
    period: str,
    transactions: list[Transaction],
    *,
    account_holder: str = "Founder Teste",
    agency: str = "0001",
    account_number: str = "12345-6",
) -> bytes:
    """Sheet 'Lançamentos': header em (2,1)/(3,1)/(4,1); dados da row 10 nas colunas data=0/desc=1/valor=3/saldo=4 (defaults de ITAU_XLS_LAYOUT)."""
    import xlwt

    wb = xlwt.Workbook()
    sh = wb.add_sheet("Lançamentos")
    sh.write(2, 1, account_holder)
    sh.write(3, 1, agency)
    sh.write(4, 1, account_number)

    yy, mm = period.split("-")
    row = 10
    sh.write(row, 0, f"01/{mm}/{yy}")
    sh.write(row, 1, "SALDO ANTERIOR")
    sh.write(row, 4, 1000.0)
    row += 1
    running = 1000.0
    for tx in sorted(transactions, key=lambda t: str(t.get("date", ""))):
        amt = float(tx.get("amount", 0))
        running += amt
        sh.write(row, 0, iso_date_to_br(str(tx.get("date", f"{period}-01"))))
        sh.write(row, 1, str(tx.get("description", "Lancamento"))[:50])
        sh.write(row, 3, amt)
        sh.write(row, 4, running)
        row += 1
    sh.write(row, 0, f"30/{mm}/{yy}")
    sh.write(row, 1, "SALDO TOTAL DISPONÍVEL DIA")
    sh.write(row, 4, running)

    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


def generate_santander_xls(
    period: str,
    transactions: list[Transaction],
    *,
    account_holder: str = "Founder Teste",
) -> bytes:
    """Sheet única: titular em (2,0), conta em (2,4), período em (4,4); dados da row 6 nas colunas data=0/desc=1/credito=4/debito=5/saldo=6, valores como string BRL (defaults de SANTANDER_XLS_LAYOUT)."""
    import xlwt

    wb = xlwt.Workbook()
    sh = wb.add_sheet("Plan1")
    yy, mm = period.split("-")
    sh.write(2, 0, account_holder)
    sh.write(2, 4, "Conta: 1652-01.001341.6")
    sh.write(4, 4, f"Extrato de 01/{mm}/{yy} a 30/{mm}/{yy}")

    row = 6
    sh.write(row, 0, f"01/{mm}/{yy}")
    sh.write(row, 1, "SALDO ANTERIOR")
    sh.write(row, 6, "1.000,00")
    row += 1
    running = 1000.0
    for tx in sorted(transactions, key=lambda t: str(t.get("date", ""))):
        amt = float(tx.get("amount", 0))
        running += amt
        sh.write(row, 0, iso_date_to_br(str(tx.get("date", f"{period}-01"))))
        sh.write(row, 1, str(tx.get("description", "Lancamento"))[:50])
        if amt >= 0:
            sh.write(row, 4, format_brl(amt))
        else:
            sh.write(row, 5, format_brl(abs(amt)))
        sh.write(row, 6, format_brl(running))
        row += 1
    sh.write(row, 0, "TOTAL")

    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()
