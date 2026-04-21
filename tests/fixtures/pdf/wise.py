"""Layout Wise (BRL) — paridade com ``scripts/e2/banks/wise.py``."""

from __future__ import annotations

from calendar import monthrange
from typing import Any

from reportlab.lib.units import cm

from tests.fixtures.pdf.formatters import format_brl

Transaction = dict


def wise_month_br(iso: str) -> tuple[int, str, int]:
    py, pm, pd = iso.strip().split("-")
    months = (
        "",
        "janeiro",
        "fevereiro",
        "março",
        "abril",
        "maio",
        "junho",
        "julho",
        "agosto",
        "setembro",
        "outubro",
        "novembro",
        "dezembro",
    )
    mi = int(pm)
    return int(pd), months[mi], int(py)


def draw_wise_extrato(
    c: Any,
    width: float,
    height: float,
    y: float,
    period: str,
    transactions: list[Transaction],
) -> tuple[float, float]:
    """Layout compatível com `scripts/e2/banks/wise.py` (BRL, linhas data após movimento)."""
    py, pm = period.split("-")
    yi, mi = int(py), int(pm)
    ld = monthrange(yi, mi)[1]
    d1, mes1, y1 = wise_month_br(f"{yi}-{mi:02d}-01")
    d2, mes2, y2 = wise_month_br(f"{yi}-{mi:02d}-{ld:02d}")
    # período textual: `1 de abril de 2026 [BRL] - 30 de abril de 2026`
    c.setFont("Helvetica", 9)
    c.drawString(2 * cm, y, "Número da conta 1234567890123456")
    y -= 0.45 * cm
    c.drawString(
        2 * cm,
        y,
        f"{d1} de {mes1} de {y1} [BRL] - {d2} de {mes2} de {y2}",
    )
    txs = sorted(transactions, key=lambda t: str(t.get("date", "")))
    running = 0.0
    for tx in txs:
        running += float(tx.get("amount", 0))

    y -= 0.45 * cm
    c.drawString(2 * cm, y, f"BRL em conta corrente  {format_brl(running)}  BRL")
    y -= 0.65 * cm
    c.setFont("Courier", 8)

    run2 = 0.0
    for tx in txs:
        if y < 3.2 * cm:
            c.showPage()
            y = height - 2 * cm
            c.setFont("Courier", 8)
        amt = float(tx.get("amount", 0))
        desc = str(tx.get("description", "Mov"))[:42]
        if amt >= 0:
            dline = f"Recebimento {desc}" if not desc.startswith("Recebimento") else desc
        else:
            dline = desc or "Debito"
        run2 += amt
        line1 = f"{dline}  {format_brl(amt)}  {format_brl(run2)}"
        c.drawString(2 * cm, y, line1[:120])
        y -= 0.36 * cm
        wd, wm, wy = wise_month_br(str(tx.get("date", f"{period}-01")))
        line2 = f"{wd} de {wm} de {wy} Transação"
        c.drawString(2 * cm, y, line2[:80])
        y -= 0.36 * cm

    y -= 0.35 * cm
    return y, run2
