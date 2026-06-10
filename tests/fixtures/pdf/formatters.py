"""Format helpers e constantes partilhadas entre os layouts de banco.

Extraído de ``tests/fixtures/pdf_generator.py`` (A6g.2 — T1.b). Convenções:
- BRL em padrão brasileiro (``1.234,56``)
- USD com vírgula milhar/ponto decimal (``12,500.00``)
- Datas ISO → ``DD/MM/YYYY`` ou ``MM/DD/YY`` para US
"""

from __future__ import annotations

from calendar import monthrange


def format_brl(value: float) -> str:
    """Formata em padrão brasileiro: `1.234,56` (sem R$ — usado em colunas)."""
    sign = "-" if value < 0 else ""
    abs_v = abs(value)
    formatted = f"{abs_v:,.2f}"
    # 1,234.56 → 1.234,56 (swap separadores)
    formatted = formatted.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{sign}{formatted}"


def format_caixa_valor_cd(amt: float) -> str:
    """Coluna valor Caixa: `1.250,50 C` ou `250,50 D` (`_parse_valor_cd`)."""
    body = format_brl(abs(amt))
    return f"{body} C" if amt >= 0 else f"{body} D"


def iso_date_to_br(iso: str) -> str:
    y, m, d = iso.strip().split("-")
    return f"{d}/{m}/{y}"


def iso_to_mmddyy_us(iso: str) -> str:
    """ISO → `MM/DD/YY` para `parse_bankofamerica` (regex de lançamentos)."""
    y, m, d = iso.strip().split("-")
    yy = int(y) % 100
    return f"{int(m):02d}/{int(d):02d}/{yy:02d}"


def format_usd_amount(val: float) -> str:
    """US: vírgula como milhar, ponto decimal (`12,500.00` / `-250.50`)."""
    neg = val < 0
    a = abs(val)
    body = f"{a:,.2f}"
    return f"-{body}" if neg else body


def period_to_br_range(period: str) -> tuple[str, str]:
    """`2026-04` → (`01/04/2026`, `30/04/2026`)."""
    py, pm = period.split("-")
    yi, mi = int(py), int(pm)
    last = monthrange(yi, mi)[1]
    return f"01/{mi:02d}/{yi}", f"{last}/{mi:02d}/{yi}"


# Nomes por índice 1–12 — alinhado a `MESES_BR_INT` em `scripts/e2/common` (regex PicPay).
MONTH_BR = (
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

# Inglês — `parse_bankofamerica` (período `for Month D, YYYY to ...`).
MONTH_EN = (
    "",
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)


__all__ = [
    "format_brl",
    "format_caixa_valor_cd",
    "format_usd_amount",
    "iso_date_to_br",
    "iso_to_mmddyy_us",
    "period_to_br_range",
    "MONTH_BR",
    "MONTH_EN",
]


def draw_text_lines(c, y: float, lines: list[str], *, step_cm: float = 0.45) -> float:
    """Desenha linhas de texto sequenciais (uma por linha lógica) e retorna o y final."""
    from reportlab.lib.units import cm

    for line in lines:
        c.drawString(2 * cm, y, line)
        y -= step_cm * cm
    return y
