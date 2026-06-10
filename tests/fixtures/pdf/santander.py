"""Layout Santander — paridade com ``scripts/e2/banks/santander.py``."""

from __future__ import annotations

from typing import Any

from reportlab.lib.units import cm

from tests.fixtures.pdf.formatters import (
    format_brl,
    iso_date_to_br,
    period_to_br_range,
)

Transaction = dict


def draw_santander_extrato(
    c: Any,
    width: float,
    height: float,
    y: float,
    period: str,
    transactions: list[Transaction],
    agency: str,
    account_number: str,
) -> tuple[float, float]:
    """Linhas compatíveis com `scripts/e2/banks/santander.py::parse_santander_conta` (regex multilinha)."""
    p_ini, p_fim = period_to_br_range(period)
    c.setFont("Helvetica", 9)
    c.drawString(2 * cm, y, f"Agência e Conta: {agency} / {account_number}")
    y -= 0.45 * cm
    c.drawString(2 * cm, y, f"Período: {p_ini} a {p_fim}")
    y -= 0.55 * cm

    txs_chrono = sorted(transactions, key=lambda t: str(t.get("date", "")))
    rows: list[tuple[Transaction, float]] = []
    running = 0.0
    for tx in txs_chrono:
        amt = float(tx.get("amount", 0))
        running += amt
        rows.append((tx, running))

    c.setFont("Courier", 8)
    # Extrato real: mais recente primeiro; o parser inverte para cronológico.
    for idx, (tx, saldo_after) in enumerate(reversed(rows)):
        if y < 3.2 * cm:
            c.showPage()
            y = height - 2 * cm
            c.setFont("Courier", 8)
        iso = str(tx.get("date", f"{period}-01"))
        br = iso_date_to_br(iso)
        desc = str(tx.get("description", "Lancamento"))[:40].upper()
        amt = float(tx.get("amount", 0))
        docto = f"{idx + 1:06d}"
        line = f"{br} {desc} {docto} {format_brl(amt)} {format_brl(saldo_after)}"
        c.drawString(2 * cm, y, line[:125])
        y -= 0.36 * cm

    final_saldo = rows[-1][1] if rows else 0.0
    return y, final_saldo


def draw_santander_unique_fatura(
    c: Any,
    width: float,
    height: float,
    y: float,
    period: str,
    transactions: list[Transaction],
    account_holder: str,
) -> tuple[float, float]:
    """Fatura Santander Unique — paridade com ``parse_santander_unique`` (header `R$ total venc fech` + `Detalhamento da Fatura` + card `NOME - NNNN XXXX XXXX NNNN`)."""
    yy, mm = period.split("-")
    holder_upper = "".join(ch for ch in account_holder.upper() if ch.isalpha() or ch == " ").strip()
    total = sum(float(t.get("amount", 0)) for t in transactions)

    c.setFont("Helvetica", 9)
    lines = [
        f"R$ {format_brl(abs(total))} 15/{mm}/{yy} 10/{mm}/{yy}",
        "Saldo Anterior 0,00",
        f"Total Despesas/Débitos no Brasil {format_brl(abs(total))}",
        "Detalhamento da Fatura",
        f"{holder_upper} - 1234 XXXX XXXX 5678",
        "Despesas",
    ]
    for line in lines:
        c.drawString(2 * cm, y, line)
        y -= 0.45 * cm

    for tx in sorted(transactions, key=lambda t: str(t.get("date", ""))):
        amt = float(tx.get("amount", 0))
        iso = str(tx.get("date", f"{period}-01"))
        _, m_iso, d_iso = iso.split("-")
        desc = str(tx.get("description", "Lancamento"))[:50]
        c.drawString(2 * cm, y, f"{d_iso}/{m_iso} {desc} {format_brl(amt)}")
        y -= 0.42 * cm
    return y, total
