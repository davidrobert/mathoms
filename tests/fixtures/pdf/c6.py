"""Layout C6 Bank — paridade com ``scripts/e2/banks/c6bank.py``."""

from __future__ import annotations

from typing import Any

from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import Table, TableStyle

from tests.fixtures.pdf.formatters import (
    MONTH_BR,
    format_brl,
    iso_date_to_br,
    period_to_br_range,
)

Transaction = dict


def draw_c6_extrato(
    c: Any,
    width: float,
    height: float,
    y: float,
    period: str,
    transactions: list[Transaction],
    account_number: str,
) -> tuple[float, float]:
    """Tabela 5 colunas — `scripts/e2/banks/c6bank.py::parse_c6bank` (`extract_tables`, `conta_pj_format`)."""
    p_ini, p_fim = period_to_br_range(period)
    y1, m1, d1 = p_ini.split("/")
    y2, m2, d2 = p_fim.split("/")
    mi1, mi2 = int(m1), int(m2)
    mes_a = MONTH_BR[mi1]
    mes_b = MONTH_BR[mi2]
    conta_digits = "".join(ch for ch in account_number if ch.isdigit()) or "12345678"

    c.setFont("Helvetica", 9)
    c.drawString(
        2 * cm,
        y,
        f"Período • {int(d1)} de {mes_a} de {y1} até {int(d2)} de {mes_b} de {y2}",
    )
    y -= 0.45 * cm
    c.drawString(2 * cm, y, f"Conta: {conta_digits}")
    y -= 0.55 * cm

    txs = sorted(transactions, key=lambda t: str(t.get("date", "")))
    data: list[list[str]] = []
    running = 0.0
    for tx in txs:
        amt = float(tx.get("amount", 0))
        br = iso_date_to_br(str(tx.get("date", f"{period}-01")))
        tipo = "Pix" if amt < 0 else "TED"
        desc = str(tx.get("description", "Lancamento"))[:40]
        running += amt
        data.append([br, "", tipo, desc, format_brl(amt)])
        # Data curta em "Saldo do dia" evita quebra de célula no pdfplumber (YY)
        saldo_br = iso_date_to_br(str(tx.get("date", f"{period}-01")))
        sd_dd, sd_mm, sd_yy = saldo_br.split("/")
        data.append(
            [
                f"Saldo do dia {sd_dd}/{sd_mm}/{sd_yy[-2:]}",
                "",
                "",
                "",
                format_brl(running),
            ]
        )

    if not data:
        data.append(["01/01/2026", "", "", "Sem movimento", "0,00"])

    table = Table(
        data,
        # Coluna 0 larga o suficiente para `Saldo do dia DD/MM/YY` (pdfplumber não quebrar célula)
        colWidths=[3.8 * cm, 0.6 * cm, 1.4 * cm, 3.6 * cm, 2.2 * cm],
    )
    table.setStyle(
        TableStyle(
            [
                ("FONT", (0, 0), (-1, -1), "Helvetica", 8),
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
