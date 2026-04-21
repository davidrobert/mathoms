"""Layout Quinto Andar (aluguel) — paridade com ``scripts/e2/banks/quintoandar.py``."""

from __future__ import annotations

from typing import Any

from reportlab.lib.units import cm

from tests.fixtures.pdf.formatters import format_brl, period_to_br_range

Transaction = dict


def format_quintoandar_valor(amt: float) -> str:
    """Item no formato do regex de `parse_quintoandar`: `R$ 1.250,00` ou `-R$ 250,50`."""
    if amt >= 0:
        return f"R$ {format_brl(amt)}"
    return f"-R$ {format_brl(abs(amt))}"


def draw_quintoandar_fatura(
    c: Any,
    width: float,
    height: float,
    y: float,
    period: str,
    transactions: list[Transaction],
) -> tuple[float, float]:
    """Texto compatível com `scripts/e2/banks/quintoandar.py::parse_quintoandar`."""
    _, p_fim = period_to_br_range(period)
    c.setFont("Helvetica", 9)
    c.drawString(2 * cm, y, "Faturas de aluguel")
    y -= 0.42 * cm
    c.drawString(2 * cm, y, "Endereco Sintetico 100 Apt Fixture")
    y -= 0.6 * cm

    txs = sorted(transactions, key=lambda t: str(t.get("date", "")))
    total = sum(float(t.get("amount", 0)) for t in txs)

    c.drawString(2 * cm, y, "Total de")
    y -= 0.36 * cm
    c.drawString(2 * cm, y, f"R$ {format_brl(total)}")
    y -= 0.55 * cm
    c.drawString(2 * cm, y, f"Receber até {p_fim}")
    y -= 0.55 * cm

    for tx in txs:
        if y < 2.5 * cm:
            c.showPage()
            y = height - 2 * cm
            c.setFont("Helvetica", 9)
        desc = str(tx.get("description", "Item"))[:55]
        amt = float(tx.get("amount", 0))
        line = f"{desc}    {format_quintoandar_valor(amt)}"
        c.drawString(2 * cm, y, line[:115])
        y -= 0.4 * cm

    return y, total
