"""Layout Santander — paridade com ``scripts/e2/banks/santander.py``."""

from __future__ import annotations

from typing import Any

from reportlab.lib.units import cm

from tests.fixtures.pdf.formatters import (
    draw_text_lines,
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
    """Fatura Santander Unique — paridade com ``parse_santander_unique`` (marcadores: ``kind == "payment"`` → seção Pagamento; ``usd`` → exterior; ``kind == "iof"`` → IOF sem data, conta no total Brasil; "Total Despesas/Débitos no Brasil" = Σ(brasil + iof))."""
    yy, mm = period.split("-")
    holder_upper = "".join(ch for ch in account_holder.upper() if ch.isalpha() or ch == " ").strip()
    c.setFont("Helvetica", 9)
    b = _santander_buckets(transactions)
    lines = _santander_unique_head(mm, yy, b) + _santander_unique_body(period, holder_upper, b)
    return draw_text_lines(c, y, lines), b["s_br"]


def _santander_buckets(transactions) -> dict:
    pay = [t for t in transactions if t.get("kind") == "payment"]
    ext = [t for t in transactions if t.get("usd")]
    iof = [t for t in transactions if t.get("kind") == "iof"]
    br = [t for t in transactions if t.get("kind") not in ("payment", "iof") and not t.get("usd")]
    return {
        "pay": pay,
        "ext": ext,
        "iof": iof,
        "br": br,
        "s_br": sum(abs(float(t.get("amount", 0))) for t in br + iof),
        "s_ext": sum(abs(float(t.get("amount", 0))) for t in ext),
        "s_ext_usd": sum(abs(float(t.get("usd", 0))) for t in ext),
        "s_pay": sum(abs(float(t.get("amount", 0))) for t in pay),
    }


def _santander_unique_head(mm, yy, b) -> list[str]:
    head = [
        f"R$ {format_brl(b['s_br'] + b['s_ext'])} 15/{mm}/{yy} 10/{mm}/{yy}",
        "Saldo Anterior 0,00",
        f"Total Despesas/Débitos no Brasil {format_brl(b['s_br'])}",
    ]
    if b["ext"]:
        head.append(
            f"Total Despesas/Débitos no Exterior {format_brl(b['s_ext'])} {format_brl(b['s_ext_usd'])}"
        )
    if b["pay"]:
        head.append(f"Total de pagamentos {format_brl(b['s_pay'])}")
    return head


def _santander_unique_body(period, holder_upper, b) -> list[str]:
    from tests.fixtures.pdf.itau import _ddmm_tx_line

    body = ["Detalhamento da Fatura", f"{holder_upper} - 1234 XXXX XXXX 5678"]
    if b["pay"]:
        body.append("Pagamento e Demais Créditos")
        body += [_ddmm_tx_line(t, period, signed=True) for t in b["pay"]]
    body.append("Despesas")
    body += [_ddmm_tx_line(t, period, signed=False) for t in b["br"]]
    for t in b["ext"]:
        body.append(_ddmm_tx_line(t, period, signed=False) + f" {format_brl(abs(float(t['usd'])))}")
    for t in b["iof"]:
        body.append(f"IOF DESPESA NO EXTERIOR {format_brl(abs(float(t.get('amount', 0))))}")
    return body
