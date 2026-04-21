"""Layout Bradesco — paridade com ``scripts/e2/banks/bradesco.py``."""

from __future__ import annotations

from calendar import monthrange
from typing import Any

from reportlab.lib.units import cm

from tests.fixtures.pdf.formatters import format_brl, period_to_br_range

Transaction = dict


def draw_bradesco_extrato(
    c: Any,
    width: float,
    height: float,
    y: float,
    period: str,
    transactions: list[Transaction],
    agency: str,
    account_number: str,
) -> tuple[float, float]:
    """Texto multilinha — `scripts/e2/banks/bradesco.py::parse_bradesco` (regex DD/MM/YY + Total)."""
    p_ini, p_fim = period_to_br_range(period)
    c.setFont("Helvetica", 9)
    c.drawString(2 * cm, y, f"Ag: {agency} | Conta: {account_number}")
    y -= 0.42 * cm
    c.drawString(2 * cm, y, f"Entre {p_ini} e {p_fim}")
    y -= 0.55 * cm

    txs = sorted(transactions, key=lambda t: str(t.get("date", "")))
    saldo_ini = 10000.0
    running = saldo_ini
    creditos = 0.0
    debitos = 0.0
    c.setFont("Courier", 8)

    # SALDO ANTERIOR — dia anterior ao início do período
    py, pm = period.split("-")
    yi, mi = int(py), int(pm)
    prev_m, prev_y = (mi - 1, yi) if mi > 1 else (12, yi - 1)
    last_prev = monthrange(prev_y, prev_m)[1]
    saldo_ant_str = f"{last_prev:02d}/{prev_m:02d}/{str(prev_y)[-2:]}"
    c.drawString(2 * cm, y, f"{saldo_ant_str} SALDO ANTERIOR {format_brl(saldo_ini)}")
    y -= 0.38 * cm

    for tx in txs:
        if y < 3 * cm:
            c.showPage()
            y = height - 2 * cm
            c.setFont("Courier", 8)
        amt = float(tx.get("amount", 0))
        desc = str(tx.get("description", "Lancamento"))[:44]
        iso = str(tx.get("date", f"{period}-01"))
        yp, mp, dp = iso.split("-")
        br = f"{dp}/{mp}/{yp[-2:]}"
        running += amt
        if amt >= 0:
            creditos += amt
            c.drawString(
                2 * cm,
                y,
                f"{br} {desc} {format_brl(amt)} {format_brl(running)}"[:118],
            )
        else:
            debitos += -amt
            c.drawString(
                2 * cm,
                y,
                f"{br} {desc} - {format_brl(-amt)} {format_brl(running)}"[:118],
            )
        y -= 0.36 * cm

    c.setFont("Courier", 8)
    c.drawString(
        2 * cm,
        y,
        f"Total {format_brl(creditos)} - {format_brl(debitos)} {format_brl(running)}"[:118],
    )
    y -= 0.4 * cm
    return y, running
