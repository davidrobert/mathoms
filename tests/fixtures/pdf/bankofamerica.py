"""Layout Bank of America (USD) — paridade com ``scripts/e2/banks/bankofamerica.py``."""

from __future__ import annotations

from calendar import monthrange
from typing import Any

from reportlab.lib.units import cm

from tests.fixtures.pdf.formatters import (
    MONTH_EN,
    format_usd_amount,
    iso_to_mmddyy_us,
)

Transaction = dict


def draw_bankofamerica_extrato(
    c: Any,
    width: float,
    height: float,
    y: float,
    period: str,
    transactions: list[Transaction],
    account_number: str,
) -> tuple[float, float]:
    """Texto compatível com `scripts/e2/banks/bankofamerica.py` (USD, regex por linha)."""
    digits = "".join(ch for ch in account_number if ch.isdigit()) or "12345678"
    acct_disp = " ".join(digits[i : i + 4] for i in range(0, len(digits), 4))

    py, pm = period.split("-")
    yi, mi = int(py), int(pm)
    last_day = monthrange(yi, mi)[1]
    mname = MONTH_EN[mi]

    c.setFont("Helvetica", 9)
    c.drawString(2 * cm, y, f"Account number: {acct_disp}")
    y -= 0.42 * cm
    c.drawString(
        2 * cm,
        y,
        f"for {mname} 1, {yi} to {mname} {last_day}, {yi}",
    )
    y -= 0.55 * cm

    txs = sorted(transactions, key=lambda t: str(t.get("date", "")))
    running = 0.0
    c.setFont("Courier", 8)
    c.drawString(2 * cm, y, "Beginning balance $0.00")
    y -= 0.38 * cm

    for tx in txs:
        if y < 3.5 * cm:
            c.showPage()
            y = height - 2 * cm
            c.setFont("Courier", 8)
        amt = float(tx.get("amount", 0))
        running += amt
        d_us = iso_to_mmddyy_us(str(tx.get("date", f"{period}-01")))
        desc = str(tx.get("description", "Transaction"))[:52]
        line = f"{d_us}  {desc}  {format_usd_amount(amt)}"
        c.drawString(2 * cm, y, line[:118])
        y -= 0.36 * cm

    if y < 3.2 * cm:
        c.showPage()
        y = height - 2 * cm
        c.setFont("Courier", 8)
    c.drawString(2 * cm, y, f"Ending balance ${format_usd_amount(running)}")
    y -= 0.45 * cm
    return y, running
