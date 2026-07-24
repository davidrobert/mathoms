"""Layout Itaú — paridade com ``scripts/e2/banks/itau.py``."""

from __future__ import annotations

from typing import Any

from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import Table, TableStyle

from tests.fixtures.pdf.formatters import (
    draw_text_lines,
    format_brl,
    iso_date_to_br,
    period_to_br_range,
)

Transaction = dict


def draw_itau_extrato(
    c: Any,
    width: float,
    height: float,
    y: float,
    period: str,
    transactions: list[Transaction],
    account_number: str,
) -> tuple[float, float]:
    """Tabela 4 colunas compatível com `scripts/e2/banks/itau.py::parse_itau` (`extract_tables`)."""
    p_ini, p_fim = period_to_br_range(period)
    c.setFont("Helvetica", 9)
    c.drawString(2 * cm, y, f"Período: {p_ini} a {p_fim}")
    y -= 0.42 * cm
    c.drawString(2 * cm, y, f"Conta: {account_number}")
    y -= 0.55 * cm

    txs = sorted(transactions, key=lambda t: str(t.get("date", "")))
    data: list[list[str]] = [
        ["Data", "Descrição", "Valor (R$)", "Saldo (R$)"],
    ]
    running = 0.0
    for tx in txs:
        amt = float(tx.get("amount", 0))
        running += amt
        br = iso_date_to_br(str(tx.get("date", f"{period}-01")))
        desc = str(tx.get("description", "Lancamento"))[:42]
        data.append(
            [
                br,
                desc,
                format_brl(amt),
                format_brl(running),
            ]
        )

    if txs:
        last_iso = str(txs[-1].get("date", f"{period}-01"))
        yp, mp, dp = last_iso.split("-")
        last_br = f"{dp}/{mp}/{yp}"
        data.append([last_br, "SALDO DO DIA", "", format_brl(running)])

    table = Table(
        data,
        colWidths=[2.8 * cm, 6.2 * cm, 3.0 * cm, 3.0 * cm],
    )
    table.setStyle(
        TableStyle(
            [
                ("FONT", (0, 0), (-1, -1), "Helvetica", 8),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
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


def draw_itau_paoacucar_fatura(
    c: Any,
    width: float,
    height: float,
    y: float,
    period: str,
    transactions: list[Transaction],
) -> tuple[float, float]:
    """Fatura Pão de Açúcar — paridade com ``parse_itau_paoacucar`` (seção `Lançamentos: compras e saques` + card `(final NNNN)`)."""
    yy, mm = period.split("-")
    total = sum(float(t.get("amount", 0)) for t in transactions)

    c.setFont("Helvetica", 9)
    return draw_text_lines(c, y, _paoacucar_lines(period, transactions, mm, yy, total)), total


def _paoacucar_lines(period, transactions, mm, yy, total) -> list[str]:
    return [
        "Cartão 1234.XXXX.5678",
        f"Vencimento: 10/{mm}/{yy}",
        f"Total desta fatura {format_brl(abs(total))}",
        f"Lançamentos atuais {format_brl(abs(total))}",
        "Lançamentos: compras e saques",
        "PAO DE ACUCAR PLATINUM(final 5678)",
        *(
            _ddmm_tx_line(tx, period, signed=False)
            for tx in sorted(transactions, key=lambda t: str(t.get("date", "")))
        ),
    ]


def _ddmm_tx_line(tx: Transaction, period: str, *, signed: bool) -> str:
    amt = float(tx.get("amount", 0))
    iso = str(tx.get("date", f"{period}-01"))
    _, m_iso, d_iso = iso.split("-")
    desc = str(tx.get("description", "Lancamento"))[:50]
    return f"{d_iso}/{m_iso} {desc} {format_brl(amt if signed else abs(amt))}"


def draw_itau_fatura(
    c: Any,
    width: float,
    height: float,
    y: float,
    period: str,
    transactions: list[Transaction],
) -> tuple[float, float]:
    """Fatura de cartão Itaú (não-cobranded) — paridade com ``parse_itau_fatura`` (marcadores: ``usd`` → internacional; ``kind == "iof"`` → "Repasse de IOF" sem data; demais → nacional; fecha Σ(lançamentos atuais) == total)."""
    yy, mm = period.split("-")
    nac, intl, iof, s_nac, s_intl, total = _itau_fatura_buckets(transactions)
    c.setFont("Helvetica", 9)
    lines = _itau_fatura_lines(period, nac, intl, iof, mm, yy, total, s_nac, s_intl)
    return draw_text_lines(c, y, lines), total


def _itau_fatura_buckets(transactions):
    nac = [t for t in transactions if not t.get("usd") and t.get("kind") != "iof"]
    intl = [t for t in transactions if t.get("usd")]
    iof = [t for t in transactions if t.get("kind") == "iof"]
    s_nac = sum(abs(float(t.get("amount", 0))) for t in nac)
    s_intl = sum(abs(float(t.get("amount", 0))) for t in intl)
    s_iof = sum(abs(float(t.get("amount", 0))) for t in iof)
    return nac, intl, iof, s_nac, s_intl, s_nac + s_intl + s_iof


def _itau_fatura_lines(period, nac, intl, iof, mm, yy, total, s_nac, s_intl) -> list[str]:
    lines = [
        "Cartão 4771.XXXX.XXXX.5739",
        "Titular TITULAR GOLDEN",
        f"Vencimento: 06/{mm}/{yy}",
        "Total da fatura anterior 0,00",
        f"Total desta fatura {format_brl(total)}",
        f"Lançamentos atuais {format_brl(total)}",
        "Lançamentos: compras e saques",
        "TITULAR GOLDEN (final 4984)",
        "DATA ESTABELECIMENTO VALOR EM R$",
        *(_ddmm_tx_line(t, period, signed=False) for t in nac),
        f"Lançamentos no cartão (final 4984) {format_brl(s_nac)}",
    ]
    if intl or iof:
        lines += _itau_fatura_intl_lines(period, intl, iof, s_intl)
    lines.append(f"Total dos lançamentos atuais {format_brl(total)}")
    return lines


def _itau_fatura_intl_lines(period, intl, iof, s_intl) -> list[str]:
    s_iof = sum(abs(float(t.get("amount", 0))) for t in iof)
    return [
        "Lançamentos internacionais",
        "TITULAR GOLDEN (final 4984)",
        "DATA ESTABELECIMENTO US$ R$",
        *(_ddmm_tx_line(t, period, signed=False) for t in intl),
        f"Total transações inter. em R$ {format_brl(s_intl)}",
        *(f"Repasse de IOF em R$ {format_brl(abs(float(t.get('amount', 0))))}" for t in iof),
        f"Total lançamentos inter. em R$ {format_brl(s_intl + s_iof)}",
    ]
