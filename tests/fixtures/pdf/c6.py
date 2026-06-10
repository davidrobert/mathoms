"""Layout C6 Bank — paridade com ``scripts/e2/banks/c6bank.py``."""

from __future__ import annotations

from typing import Any

from reportlab.lib.units import cm

from tests.fixtures.pdf.formatters import (
    MONTH_BR,
    draw_text_lines,
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
    """Layout C6 PDF — formato `DD/MM DD/MM <tipo> <descrição> [-]R$ X,XX` + `Saldo do dia`."""
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
    running = 0.0
    line_height = 0.42 * cm
    for tx in txs:
        amt = float(tx.get("amount", 0))
        br = iso_date_to_br(str(tx.get("date", f"{period}-01")))
        dd, mm, yyyy = br.split("/")
        # Formato real: dois pares DD/MM (movimentação e competência) + tipo +
        # descrição + valor com prefixo R$ e sinal. Linha única por transação.
        tipo = "Saída PIX" if amt < 0 else "Entrada PIX"
        desc = str(tx.get("description", "Lancamento"))[:60]
        sinal = "-" if amt < 0 else ""
        valor_str = format_brl(abs(amt))
        if y < 2.5 * cm:
            c.showPage()
            y = height - 2.5 * cm
            c.setFont("Helvetica", 9)
        c.drawString(
            2 * cm,
            y,
            f"{dd}/{mm} {dd}/{mm} {tipo} {desc} {sinal}R$ {valor_str}",
        )
        y -= line_height
        running += amt
        c.drawString(
            2 * cm,
            y,
            f"Saldo do dia {dd}/{mm}/{yyyy[-2:]} R$ {format_brl(running)}",
        )
        y -= line_height + 0.1 * cm

    if not txs:
        c.drawString(2 * cm, y, "Sem movimento no período")
        y -= line_height

    return y, running


_MONTH_ABBR_BR = (
    "jan",
    "fev",
    "mar",
    "abr",
    "mai",
    "jun",
    "jul",
    "ago",
    "set",
    "out",
    "nov",
    "dez",
)
_MONTH_FULL_BR = (
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


def draw_c6_carbon_fatura(
    c: Any,
    width: float,
    height: float,
    y: float,
    period: str,
    transactions: list[Transaction],
    account_holder: str,
) -> tuple[float, float]:
    """Fatura C6 Carbon — paridade com ``parse_c6_carbon`` (linhas `D mes DESC VALOR`)."""
    yy, mm = period.split("-")
    month_idx = int(mm) - 1
    holder_upper = account_holder.upper()

    total = sum(float(t.get("amount", 0)) for t in transactions)
    c.setFont("Helvetica", 9)
    y = draw_text_lines(c, y, _carbon_lines(period, transactions, holder_upper, month_idx, total))
    return y, total


def _carbon_lines(period, transactions, holder_upper, month_idx, total) -> list[str]:
    return [
        f"Vencimento: 15 de {_MONTH_FULL_BR[month_idx]}",
        f"Valor da fatura: R$ {format_brl(abs(total))}",
        "Limite total: R$ 50.000,00",
        f"C6 Carbon Final 1234 - {holder_upper} Cartão",
        *(
            _carbon_tx_line(tx, period)
            for tx in sorted(transactions, key=lambda t: str(t.get("date", "")))
        ),
        f"Subtotal deste cartão R$ {format_brl(abs(total))}",
    ]


def _carbon_tx_line(tx: Transaction, period: str) -> str:
    amt = float(tx.get("amount", 0))
    iso = str(tx.get("date", f"{period}-01"))
    day = int(iso.split("-")[2])
    abbr = _MONTH_ABBR_BR[int(iso.split("-")[1]) - 1]
    desc = str(tx.get("description", "Lancamento"))[:50]
    return f"{day} {abbr} {desc} {format_brl(abs(amt))}"
