"""Layout PicPay — paridade com ``scripts/e2/banks/picpay.py``."""

from __future__ import annotations

from calendar import monthrange
from typing import Any

from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import Table, TableStyle

from tests.fixtures.pdf.formatters import (
    MONTH_BR,
    format_brl,
    iso_date_to_br,
)

Transaction = dict


def draw_picpay_extrato(
    c: Any,
    width: float,
    height: float,
    y: float,
    period: str,
    transactions: list[Transaction],
    account_number: str,
) -> tuple[float, float]:
    """Tabela ReportLab compatível com `scripts/e2/banks/picpay.py` (`extract_tables`)."""
    digits = "".join(ch for ch in account_number if ch.isdigit()) or "12345"
    py, pm = period.split("-")
    yi, mi = int(py), int(pm)
    last_day = monthrange(yi, mi)[1]
    mes = MONTH_BR[mi]

    c.setFont("Helvetica", 9)
    c.drawString(2 * cm, y, f"Conta: {digits}")
    y -= 0.45 * cm
    mov_line = f"MOVIMENTAÇÕES 1 DE {mes} DE {yi} A {last_day} DE {mes} DE {yi}"
    c.drawString(2 * cm, y, mov_line[:100])
    y -= 0.55 * cm

    txs = sorted(transactions, key=lambda t: str(t.get("date", "")))
    data: list[list[str]] = [
        ["Data/Hora", "Descrição", "Valor (R$)", "Saldo (R$)"],
    ]
    running = 0.0
    for tx in txs:
        amt = float(tx.get("amount", 0))
        running += amt
        br = iso_date_to_br(str(tx.get("date", f"{period}-01")))
        desc = str(tx.get("description", "Lancamento"))[:55]
        data.append(
            [
                br,
                desc,
                format_brl(amt),
                format_brl(running),
            ]
        )
    final_bal = running

    table = Table(
        data,
        colWidths=[3.2 * cm, 7.5 * cm, 3.0 * cm, 3.0 * cm],
    )
    table.setStyle(
        TableStyle(
            [
                ("FONT", (0, 0), (-1, -1), "Helvetica", 8),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    avail_w = width - 4 * cm
    tw, th = table.wrapOn(c, avail_w, height)
    if y - th < 2 * cm:
        c.showPage()
        y = height - 2.5 * cm
        tw, th = table.wrapOn(c, avail_w, height)
    table.drawOn(c, 2 * cm, y - th)
    y = y - th - 0.45 * cm
    return y, final_bal
