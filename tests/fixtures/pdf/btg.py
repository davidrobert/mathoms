"""Layout BTG Pactual — paridade com ``scripts/e2/banks/btg.py``."""

from __future__ import annotations

from typing import Any

from reportlab.lib.units import cm

from tests.fixtures.pdf.formatters import (
    format_brl,
    iso_date_to_br,
    period_to_br_range,
)

Transaction = dict


def draw_btgpactual_movimentacao(
    c: Any,
    width: float,
    height: float,
    y: float,
    period: str,
    transactions: list[Transaction],
) -> tuple[float, float]:
    """Bloco de texto compatível com `scripts/e2/banks/btg.py` (regex Movimentação)."""
    p_ini, p_fim = period_to_br_range(period)
    c.setFont("Helvetica", 9)
    c.drawString(2 * cm, y, f"Período de {p_ini} a {p_fim}")
    y -= 0.45 * cm
    c.drawString(2 * cm, y, "Conta Corrente: 123456789")
    y -= 0.7 * cm
    c.setFont("Helvetica-Bold", 10)
    c.drawString(2 * cm, y, "Movimentação Conta Corrente")
    y -= 0.45 * cm
    c.setFont("Helvetica-Bold", 8)
    c.drawString(2 * cm, y, "Data Descrição Valor Saldo")
    y -= 0.4 * cm
    c.setFont("Courier", 8)

    txs = sorted(transactions, key=lambda t: str(t.get("date", "")))
    running = 0.0

    si_line = f"{p_ini}  Saldo Inicial  {format_brl(0)}"
    c.drawString(2 * cm, y, si_line[:120])
    y -= 0.38 * cm

    for tx in txs:
        if y < 2.5 * cm:
            c.showPage()
            y = height - 2 * cm
            c.setFont("Courier", 8)
        amt = float(tx.get("amount", 0))
        br_d = iso_date_to_br(str(tx.get("date", ""))) if tx.get("date") else p_ini
        raw_desc = str(tx.get("description", "Lancamento"))[:44]
        if amt >= 0:
            desc = raw_desc if "Recebimento" in raw_desc else f"Recebimento {raw_desc}"
        else:
            desc = raw_desc if raw_desc else "Debito"

        valor_abs = format_brl(abs(amt))
        running += amt
        saldo = format_brl(running)
        line = f"{br_d}  {desc}  {valor_abs}  {saldo}"
        c.drawString(2 * cm, y, line[:130])
        y -= 0.38 * cm

    if y < 2.2 * cm:
        c.showPage()
        y = height - 2 * cm
        c.setFont("Courier", 8)
    sf_line = f"{p_fim}  Saldo Final  {format_brl(running)}"
    c.drawString(2 * cm, y, sf_line[:120])
    y -= 0.5 * cm
    return y, running
