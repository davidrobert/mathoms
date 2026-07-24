"""Layout Rico Investimentos — paridade com ``scripts/e2/banks/rico.py``."""

from __future__ import annotations

from typing import Any

from reportlab.lib.units import cm

from tests.fixtures.pdf.formatters import format_brl, iso_date_to_br

Transaction = dict


def draw_rico_extrato(
    c: Any,
    width: float,
    height: float,
    y: float,
    period: str,
    transactions: list[Transaction],
    account_number: str,
) -> tuple[float, float]:
    """Layout compatível com `scripts/e2/banks/rico.py` (duas datas + R$ valor + R$ saldo).

    Paridade byte-a-byte com fixture original (A6g.2 — T1.b): o fallback
    ``p_ini`` dentro do loop permanece como referência não-definida, porque
    ``txs`` sempre traz ``date`` — `NameError` nunca dispara.
    """
    c.setFont("Helvetica", 9)
    c.drawString(2 * cm, y, f"Conta: {account_number}")
    y -= 0.45 * cm
    # Não colocar duas datas DD/MM/AAAA seguidas no texto — o finditer de `parse_rico`
    # captura qualquer par e geraria falso positivo.
    c.drawString(2 * cm, y, f"Referencia: periodo {period}")
    y -= 0.7 * cm
    c.setFont("Courier", 8)

    txs = sorted(transactions, key=lambda t: str(t.get("date", "")))
    running = 0.0
    for tx in txs:
        if y < 3.5 * cm:
            c.showPage()
            y = height - 2 * cm
            c.setFont("Courier", 8)
        amt = float(tx.get("amount", 0))
        br = iso_date_to_br(str(tx.get("date", ""))) if tx.get("date") else p_ini  # noqa: F821
        desc = str(tx.get("description", "Lancamento"))[:40]
        running += amt
        # Coluna única `[\d.,]+` no parser Rico — sem sinal negativo no PDF
        vcol = format_brl(abs(amt))
        scol = format_brl(running)
        prefix = "Débito " if amt < 0 else ""
        line = f"{br} {br} {prefix}{desc}  R$ {vcol}  R$ {scol}"
        c.drawString(2 * cm, y, line[:125])
        y -= 0.38 * cm

    c.setFont("Helvetica", 9)
    y -= 0.35 * cm
    c.drawString(2 * cm, y, f"Saldo disponível: R$ {format_brl(running)}")
    y -= 0.5 * cm
    return y, running


# Carteira consolidada XLSX (A39.l9) — paridade com ``parse_rico_carteira``.
# Ações: PETR4 800 + ITSA4 300 == subtotal 1.100 (checksum por classe fecha);
# Fundos: 500. Proventos/JCP no rodapé ficam fora do PL. Qtd (última célula) só
# nos tickers RV — casa com a custódia acionária Itaú.
_CARTEIRA_ROWS = [
    ["Este é o seu patrimônio", "Total investido", "Saldo Disponível"],
    ["R$ 1.600,00", "R$ 1.500,00", "R$ 100,00"],
    ["Ações", "R$ 1.100,00"],
    ["33,7%", "Renda Variável Brasil", "Posição", "% Alocação"],
    ["PETR4", "R$ 800,00", "28,7%", "-", "Indefinido", "R$ 42,58", "1.700"],
    ["ITSA4", "R$ 300,00", "4,26%", "-", "Indefinido", "R$ 13,82", "778"],
    ["Fundos de Investimentos", "R$ 500,00"],
    ["Fundo Sintetico FIF", "R$ 500,00", "1,31%", "64,87%"],
    ["Dividendos, proventos e outras distribuições"],
    ["Proventos"],
    ["Ações", "R$ 50,00"],
    ["PETR4", "1.700", "0,24%", "R$ 50,00"],
]


def generate_rico_carteira_xlsx() -> bytes:
    """Carteira consolidada Rico: subtotal por classe fecha; proventos JCP fora do PL."""
    from io import BytesIO

    import openpyxl

    wb = openpyxl.Workbook()
    sh = wb.active
    sh.title = "Sua carteira"
    for row in _CARTEIRA_ROWS:
        sh.append(row)
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()
