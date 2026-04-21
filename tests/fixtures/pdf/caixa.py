"""Layout Caixa Econômica Federal — paridade com ``scripts/e2/banks/caixa.py``."""

from __future__ import annotations

from typing import Any

from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import Table, TableStyle

from tests.fixtures.pdf.formatters import (
    format_brl,
    format_caixa_valor_cd,
    iso_date_to_br,
    period_to_br_range,
)

Transaction = dict


def draw_caixa_extrato(
    c: Any,
    width: float,
    height: float,
    y: float,
    period: str,
    transactions: list[Transaction],
    agency: str,
    account_number: str,
) -> tuple[float, float]:
    """Tabela 7 colunas + texto — `scripts/e2/banks/caixa.py::parse_caixa` (`extract_tables`)."""
    p_ini, p_fim = period_to_br_range(period)
    c.setFont("Helvetica", 9)
    c.drawString(2 * cm, y, f"Conta {agency} / {account_number}")
    y -= 0.4 * cm
    c.drawString(2 * cm, y, f"Período dos lançamentos {p_ini} até {p_fim}")
    y -= 0.4 * cm
    c.drawString(2 * cm, y, "SALDO ANTERIOR R$ 0,00 C")
    y -= 0.55 * cm

    txs = sorted(transactions, key=lambda t: str(t.get("date", "")))
    data: list[list[str]] = [
        ["Data Mov.", "Nr. Doc", "Histórico", "Favorecido", "", "Valor", "Saldo"],
    ]
    running = 0.0
    for i, tx in enumerate(txs):
        amt = float(tx.get("amount", 0))
        running += amt
        br = iso_date_to_br(str(tx.get("date", f"{period}-01")))
        desc = str(tx.get("description", "Lancamento"))[:28]
        val_cell = format_caixa_valor_cd(amt)
        saldo_cell = f"{format_brl(running)} C"
        data.append([br, str(i + 1), desc, "", "", val_cell, saldo_cell])

    if txs:
        last_iso = str(txs[-1].get("date", f"{period}-01"))
        yp, mp, dp = last_iso.split("-")
        last_br = f"{dp}/{mp}/{yp}"
        data.append(
            [last_br, "", "SALDO DIA", "", "", "", f"{format_brl(running)} C"]
        )

    table = Table(
        data,
        colWidths=[2.0 * cm, 1.0 * cm, 3.2 * cm, 1.8 * cm, 0.6 * cm, 2.2 * cm, 2.2 * cm],
    )
    table.setStyle(
        TableStyle(
            [
                ("FONT", (0, 0), (-1, -1), "Helvetica", 7),
                ("GRID", (0, 0), (-1, -1), 0.2, colors.grey),
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
    return y, running
