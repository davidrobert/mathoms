"""Synthetic PDF generator — F6.5 (sub-fase 6.5F.12).

Gera fatura/extrato sintético por banco para uso em tests (E2E + integration).
Substitui qualquer PDF real em `tests/`, eliminando risco LGPD (ADR-063).

# Por que reportlab e não weasyprint?
- Sem dependência de Cairo/Pango (instalação trivial em Linux/macOS/Windows).
- Determinístico: PDF gerado byte-a-byte idêntico para o mesmo input.
- Pequeno: deps em <5MB.

# Determinismo
- Datas pinned via parâmetro `creation_date` (default 2026-04-15T12:00:00Z).
- Fonts: usar apenas Helvetica/Courier (built-in PDF, sem subset variável).
- Sem timestamps/IDs aleatórios — todos derivados do seed.
- `setProducer` desabilitado para não vazar versão da lib em diff de bytes.

# Bancos cobertos (14 — alinhado com `config/institutions.json` + `scripts/e2/registry.py`)
# Layout dedicado: BTG, Rico, Wise, PicPay, Bank of America, Santander, Itaú, Caixa — `_draw_*`.
# Demais: tabela genérica até evolução incremental.
- Brasileiros: c6bank, itau, santander, bradesco, btgpactual, rico, picpay, caixa
- Internacionais: bankofamerica, wise, binance
- Outros: quintoandar (aluguel), receitafederal (IRPF), einstein (saúde)

Cada banco tem layout próprio em `_LAYOUTS[banco]`; a estrutura mínima é:
- header (logo placeholder + nome/CNPJ + período)
- conta (titular + agência + conta)
- transações (data, descrição, valor, saldo)
- footer (totais + página)

# CPFs e nomes
NUNCA usar CPFs reais. Os defaults aqui são `000.000.000-00` (placeholder) e
nomes obviamente fictícios. Tests que precisam CPF válido mod-11 devem usar
o gerador determinístico em `tests/utils/cpf.py` (criado em 6.5D.7) e passar
explicitamente.

# Uso
    from tests.fixtures.pdf_generator import generate_statement, BankCode

    pdf_bytes = generate_statement(
        bank="c6bank",
        kind="extrato",
        period="2026-04",
        transactions=[
            {"date": "2026-04-05", "description": "Mercado XYZ", "amount": -250.50},
            {"date": "2026-04-01", "description": "Pagto Folha", "amount": 12500.00},
        ],
        account_holder="Founder Teste",
        account_number="12345-6",
        agency="0001",
    )

    # ou diretamente para arquivo:
    write_statement_pdf("/tmp/c6_2026_04.pdf", bank="c6bank", ...)

# CI: regenerar fixtures determinísticas
A pasta `tests/fixtures/pdfs/` contém PDFs canonical regenerados pelo CI.
Ver `tests/fixtures/regenerate_pdfs.py` para o script (criado em sub-task
posterior).
"""

from __future__ import annotations

from calendar import monthrange
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any, Literal, TypedDict

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.pdfgen import canvas
    from reportlab.platypus import Table, TableStyle
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "tests/fixtures/pdf_generator.py requer reportlab. "
        "Instale com `pip install reportlab` ou via requirements-dev.txt."
    ) from exc


BankCode = Literal[
    "c6bank",
    "itau",
    "santander",
    "bradesco",
    "btgpactual",
    "rico",
    "picpay",
    "caixa",
    "bankofamerica",
    "wise",
    "binance",
    "quintoandar",
    "receitafederal",
    "einstein",
]

DocKind = Literal["extrato", "fatura"]


class Transaction(TypedDict, total=False):
    date: str  # YYYY-MM-DD
    description: str
    amount: float  # negativo = débito, positivo = crédito
    category: str  # opcional
    balance: float  # opcional, saldo após


# ── Layout base por banco — header customizável ──────────────────────────
_BANK_LABELS: dict[str, dict[str, str]] = {
    "c6bank": {"name": "Banco C6 S.A.", "cnpj": "31.872.495/0001-72"},
    "itau": {"name": "Itaú Unibanco S.A.", "cnpj": "60.701.190/0001-04"},
    "santander": {"name": "Banco Santander (Brasil) S.A.", "cnpj": "90.400.888/0001-42"},
    "bradesco": {"name": "Banco Bradesco S.A.", "cnpj": "60.746.948/0001-12"},
    "btgpactual": {"name": "Banco BTG Pactual S.A.", "cnpj": "30.306.294/0001-45"},
    "rico": {"name": "Rico Investimentos (XP)", "cnpj": "02.332.886/0011-78"},
    "picpay": {"name": "PicPay Servicos S.A.", "cnpj": "22.896.431/0001-10"},
    "caixa": {"name": "Caixa Economica Federal", "cnpj": "00.360.305/0001-04"},
    "bankofamerica": {"name": "Bank of America N.A.", "cnpj": "—"},
    "wise": {"name": "Wise Payments Limited", "cnpj": "—"},
    "binance": {"name": "Binance Holdings Limited", "cnpj": "—"},
    "quintoandar": {"name": "Quinto Andar Servicos Imobiliarios", "cnpj": "26.466.939/0001-87"},
    "receitafederal": {"name": "Receita Federal do Brasil", "cnpj": "—"},
    "einstein": {"name": "Hospital Israelita Albert Einstein", "cnpj": "—"},
}


def _format_brl(value: float) -> str:
    """Formata em padrão brasileiro: `1.234,56` (sem R$ — usado em colunas)."""
    sign = "-" if value < 0 else ""
    abs_v = abs(value)
    formatted = f"{abs_v:,.2f}"
    # 1,234.56 → 1.234,56 (swap separadores)
    formatted = formatted.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{sign}{formatted}"


def _format_caixa_valor_cd(amt: float) -> str:
    """Coluna valor Caixa: `1.250,50 C` ou `250,50 D` (`_parse_valor_cd`)."""
    body = _format_brl(abs(amt))
    return f"{body} C" if amt >= 0 else f"{body} D"


def _iso_date_to_br(iso: str) -> str:
    y, m, d = iso.strip().split("-")
    return f"{d}/{m}/{y}"


def _iso_to_mmddyy_us(iso: str) -> str:
    """ISO → `MM/DD/YY` para `parse_bankofamerica` (regex de lançamentos)."""
    y, m, d = iso.strip().split("-")
    yy = int(y) % 100
    return f"{int(m):02d}/{int(d):02d}/{yy:02d}"


def _format_usd_amount(val: float) -> str:
    """US: vírgula como milhar, ponto decimal (`12,500.00` / `-250.50`)."""
    neg = val < 0
    a = abs(val)
    body = f"{a:,.2f}"
    return f"-{body}" if neg else body


def _period_to_br_range(period: str) -> tuple[str, str]:
    """`2026-04` → (`01/04/2026`, `30/04/2026`)."""
    py, pm = period.split("-")
    yi, mi = int(py), int(pm)
    last = monthrange(yi, mi)[1]
    return f"01/{mi:02d}/{yi}", f"{last}/{mi:02d}/{yi}"


# Nomes por índice 1–12 — alinhado a `MESES_BR_INT` em `scripts/e2/common` (regex PicPay).
_MONTH_BR = (
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
_MONTH_EN = (
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


def _draw_btgpactual_movimentacao(
    c: Any,
    width: float,
    height: float,
    y: float,
    period: str,
    transactions: list[Transaction],
) -> tuple[float, float]:
    """Bloco de texto compatível com `scripts/e2/banks/btg.py` (regex Movimentação)."""
    p_ini, p_fim = _period_to_br_range(period)
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

    si_line = f"{p_ini}  Saldo Inicial  {_format_brl(0)}"
    c.drawString(2 * cm, y, si_line[:120])
    y -= 0.38 * cm

    for tx in txs:
        if y < 2.5 * cm:
            c.showPage()
            y = height - 2 * cm
            c.setFont("Courier", 8)
        amt = float(tx.get("amount", 0))
        br_d = _iso_date_to_br(str(tx.get("date", ""))) if tx.get("date") else p_ini
        raw_desc = str(tx.get("description", "Lancamento"))[:44]
        if amt >= 0:
            desc = raw_desc if "Recebimento" in raw_desc else f"Recebimento {raw_desc}"
        else:
            desc = raw_desc if raw_desc else "Debito"

        valor_abs = _format_brl(abs(amt))
        running += amt
        saldo = _format_brl(running)
        line = f"{br_d}  {desc}  {valor_abs}  {saldo}"
        c.drawString(2 * cm, y, line[:130])
        y -= 0.38 * cm

    if y < 2.2 * cm:
        c.showPage()
        y = height - 2 * cm
        c.setFont("Courier", 8)
    sf_line = f"{p_fim}  Saldo Final  {_format_brl(running)}"
    c.drawString(2 * cm, y, sf_line[:120])
    y -= 0.5 * cm
    return y, running


def _draw_rico_extrato(
    c: Any,
    width: float,
    height: float,
    y: float,
    period: str,
    transactions: list[Transaction],
    account_number: str,
) -> tuple[float, float]:
    """Layout compatível com `scripts/e2/banks/rico.py` (duas datas + R$ valor + R$ saldo)."""
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
        br = _iso_date_to_br(str(tx.get("date", ""))) if tx.get("date") else p_ini
        desc = str(tx.get("description", "Lancamento"))[:40]
        running += amt
        # Coluna única `[\d.,]+` no parser Rico — sem sinal negativo no PDF
        vcol = _format_brl(abs(amt))
        scol = _format_brl(running)
        prefix = "Débito " if amt < 0 else ""
        line = f"{br} {br} {prefix}{desc}  R$ {vcol}  R$ {scol}"
        c.drawString(2 * cm, y, line[:125])
        y -= 0.38 * cm

    c.setFont("Helvetica", 9)
    y -= 0.35 * cm
    c.drawString(2 * cm, y, f"Saldo disponível: R$ {_format_brl(running)}")
    y -= 0.5 * cm
    return y, running


def _wise_month_br(iso: str) -> tuple[int, str, int]:
    py, pm, pd = iso.strip().split("-")
    months = (
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
    mi = int(pm)
    return int(pd), months[mi], int(py)


def _draw_wise_extrato(
    c: Any,
    width: float,
    height: float,
    y: float,
    period: str,
    transactions: list[Transaction],
) -> tuple[float, float]:
    """Layout compatível com `scripts/e2/banks/wise.py` (BRL, linhas data após movimento)."""
    py, pm = period.split("-")
    yi, mi = int(py), int(pm)
    ld = monthrange(yi, mi)[1]
    d1, mes1, y1 = _wise_month_br(f"{yi}-{mi:02d}-01")
    d2, mes2, y2 = _wise_month_br(f"{yi}-{mi:02d}-{ld:02d}")
    # período textual: `1 de abril de 2026 [BRL] - 30 de abril de 2026`
    c.setFont("Helvetica", 9)
    c.drawString(2 * cm, y, "Número da conta 1234567890123456")
    y -= 0.45 * cm
    c.drawString(
        2 * cm,
        y,
        f"{d1} de {mes1} de {y1} [BRL] - {d2} de {mes2} de {y2}",
    )
    txs = sorted(transactions, key=lambda t: str(t.get("date", "")))
    running = 0.0
    for tx in txs:
        running += float(tx.get("amount", 0))

    y -= 0.45 * cm
    c.drawString(2 * cm, y, f"BRL em conta corrente  {_format_brl(running)}  BRL")
    y -= 0.65 * cm
    c.setFont("Courier", 8)

    run2 = 0.0
    for tx in txs:
        if y < 3.2 * cm:
            c.showPage()
            y = height - 2 * cm
            c.setFont("Courier", 8)
        amt = float(tx.get("amount", 0))
        desc = str(tx.get("description", "Mov"))[:42]
        if amt >= 0:
            dline = f"Recebimento {desc}" if not desc.startswith("Recebimento") else desc
        else:
            dline = desc or "Debito"
        run2 += amt
        line1 = f"{dline}  {_format_brl(amt)}  {_format_brl(run2)}"
        c.drawString(2 * cm, y, line1[:120])
        y -= 0.36 * cm
        wd, wm, wy = _wise_month_br(str(tx.get("date", f"{period}-01")))
        line2 = f"{wd} de {wm} de {wy} Transação"
        c.drawString(2 * cm, y, line2[:80])
        y -= 0.36 * cm

    y -= 0.35 * cm
    return y, run2


def _draw_picpay_extrato(
    c: Any,
    width: float,
    height: float,
    y: float,
    period: str,
    transactions: list[Transaction],
    account_number: str,
) -> tuple[float, float]:
    """Tabela ReportLab compatível com `scripts/e2/banks/picpay.py` (`extract_tables`)."""
    digits = "".join(ch for ch in account_number if ch.isdigit()) or "12345"
    py, pm = period.split("-")
    yi, mi = int(py), int(pm)
    last_day = monthrange(yi, mi)[1]
    mes = _MONTH_BR[mi]

    c.setFont("Helvetica", 9)
    c.drawString(2 * cm, y, f"Conta: {digits}")
    y -= 0.45 * cm
    mov_line = f"MOVIMENTAÇÕES 1 DE {mes} DE {yi} A {last_day} DE {mes} DE {yi}"
    c.drawString(2 * cm, y, mov_line[:100])
    y -= 0.55 * cm

    txs = sorted(transactions, key=lambda t: str(t.get("date", "")))
    data: list[list[str]] = [
        ["Data/Hora", "Descrição", "Valor (R$)", "Saldo (R$)"],
    ]
    running = 0.0
    for tx in txs:
        amt = float(tx.get("amount", 0))
        running += amt
        br = _iso_date_to_br(str(tx.get("date", f"{period}-01")))
        desc = str(tx.get("description", "Lancamento"))[:55]
        data.append(
            [
                br,
                desc,
                _format_brl(amt),
                _format_brl(running),
            ]
        )
    final_bal = running

    table = Table(
        data,
        colWidths=[3.2 * cm, 7.5 * cm, 3.0 * cm, 3.0 * cm],
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
    return y, final_bal


def _draw_bankofamerica_extrato(
    c: Any,
    width: float,
    height: float,
    y: float,
    period: str,
    transactions: list[Transaction],
    account_number: str,
) -> tuple[float, float]:
    """Texto compatível com `scripts/e2/banks/bankofamerica.py` (USD, regex por linha)."""
    digits = "".join(ch for ch in account_number if ch.isdigit()) or "12345678"
    acct_disp = " ".join(digits[i : i + 4] for i in range(0, len(digits), 4))

    py, pm = period.split("-")
    yi, mi = int(py), int(pm)
    last_day = monthrange(yi, mi)[1]
    mname = _MONTH_EN[mi]

    c.setFont("Helvetica", 9)
    c.drawString(2 * cm, y, f"Account number: {acct_disp}")
    y -= 0.42 * cm
    c.drawString(
        2 * cm,
        y,
        f"for {mname} 1, {yi} to {mname} {last_day}, {yi}",
    )
    y -= 0.55 * cm

    txs = sorted(transactions, key=lambda t: str(t.get("date", "")))
    running = 0.0
    c.setFont("Courier", 8)
    c.drawString(2 * cm, y, "Beginning balance $0.00")
    y -= 0.38 * cm

    for tx in txs:
        if y < 3.5 * cm:
            c.showPage()
            y = height - 2 * cm
            c.setFont("Courier", 8)
        amt = float(tx.get("amount", 0))
        running += amt
        d_us = _iso_to_mmddyy_us(str(tx.get("date", f"{period}-01")))
        desc = str(tx.get("description", "Transaction"))[:52]
        line = f"{d_us}  {desc}  {_format_usd_amount(amt)}"
        c.drawString(2 * cm, y, line[:118])
        y -= 0.36 * cm

    if y < 3.2 * cm:
        c.showPage()
        y = height - 2 * cm
        c.setFont("Courier", 8)
    c.drawString(2 * cm, y, f"Ending balance ${_format_usd_amount(running)}")
    y -= 0.45 * cm
    return y, running


def _draw_santander_extrato(
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
    p_ini, p_fim = _period_to_br_range(period)
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
        br = _iso_date_to_br(iso)
        desc = str(tx.get("description", "Lancamento"))[:40].upper()
        amt = float(tx.get("amount", 0))
        docto = f"{idx + 1:06d}"
        line = f"{br} {desc} {docto} {_format_brl(amt)} {_format_brl(saldo_after)}"
        c.drawString(2 * cm, y, line[:125])
        y -= 0.36 * cm

    final_saldo = rows[-1][1] if rows else 0.0
    return y, final_saldo


def _draw_itau_extrato(
    c: Any,
    width: float,
    height: float,
    y: float,
    period: str,
    transactions: list[Transaction],
    account_number: str,
) -> tuple[float, float]:
    """Tabela 4 colunas compatível com `scripts/e2/banks/itau.py::parse_itau` (`extract_tables`)."""
    p_ini, p_fim = _period_to_br_range(period)
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
        br = _iso_date_to_br(str(tx.get("date", f"{period}-01")))
        desc = str(tx.get("description", "Lancamento"))[:42]
        data.append(
            [
                br,
                desc,
                _format_brl(amt),
                _format_brl(running),
            ]
        )

    if txs:
        last_iso = str(txs[-1].get("date", f"{period}-01"))
        yp, mp, dp = last_iso.split("-")
        last_br = f"{dp}/{mp}/{yp}"
        data.append([last_br, "SALDO DO DIA", "", _format_brl(running)])

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


def _draw_caixa_extrato(
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
    p_ini, p_fim = _period_to_br_range(period)
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
        br = _iso_date_to_br(str(tx.get("date", f"{period}-01")))
        desc = str(tx.get("description", "Lancamento"))[:28]
        val_cell = _format_caixa_valor_cd(amt)
        saldo_cell = f"{_format_brl(running)} C"
        data.append([br, str(i + 1), desc, "", "", val_cell, saldo_cell])

    if txs:
        last_iso = str(txs[-1].get("date", f"{period}-01"))
        yp, mp, dp = last_iso.split("-")
        last_br = f"{dp}/{mp}/{yp}"
        data.append(
            [last_br, "", "SALDO DIA", "", "", "", f"{_format_brl(running)} C"]
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


def generate_statement(
    bank: BankCode,
    kind: DocKind = "extrato",
    *,
    period: str = "2026-04",
    transactions: list[Transaction] | None = None,
    account_holder: str = "Founder Teste",
    account_number: str = "12345-6",
    agency: str = "0001",
    cpf: str = "000.000.000-00",
    creation_date: datetime | None = None,
) -> bytes:
    """Gera bytes de um PDF sintético determinístico para o banco/tipo dados.

    Returns:
        bytes do PDF — pode ser escrito em arquivo ou consumido em memória.

    O conteúdo é simples (1 página A4) com texto extraível. Layouts dedicados:
    **btgpactual**, **rico**, **wise**, **picpay**, **bankofamerica**, **santander**, **itau**, **caixa** — demais:
    tabela genérica (ISO nas linhas) — evolução incremental.
    """
    if bank not in _BANK_LABELS:
        raise ValueError(f"Banco desconhecido: {bank}. Adicione em _BANK_LABELS.")

    transactions = transactions or []
    creation_date = creation_date or datetime(2026, 4, 15, 12, 0, 0, tzinfo=timezone.utc)

    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4

    # ─── Determinismo: sem metadata variável ───
    c.setProducer("")  # remove "ReportLab vX.Y" do output
    c.setCreator("Fin Synthetic PDF Generator (test fixture)")
    c.setTitle(f"{kind} {bank} {period}")
    c.setAuthor("test-fixture")
    # PDF stream timestamp pinned via setStandardFonts; reportlab usa os
    # default metadata 'D:20000101000000Z' quando não setamos via _doc.

    # ─── Header ───
    label = _BANK_LABELS[bank]
    c.setFont("Helvetica-Bold", 14)
    c.drawString(2 * cm, height - 2 * cm, label["name"])
    c.setFont("Helvetica", 8)
    c.drawString(2 * cm, height - 2.5 * cm, f"CNPJ: {label['cnpj']}")
    c.drawString(2 * cm, height - 2.9 * cm, f"Periodo: {period}")
    c.drawString(width - 6 * cm, height - 2 * cm,
                 f"{'Extrato de Conta' if kind == 'extrato' else 'Fatura de Cartao'}")

    # ─── Conta / Titular ───
    y = height - 4 * cm
    c.setFont("Helvetica-Bold", 10)
    c.drawString(2 * cm, y, "Titular:")
    c.setFont("Helvetica", 10)
    c.drawString(4 * cm, y, account_holder)
    y -= 0.5 * cm
    c.setFont("Helvetica-Bold", 10)
    c.drawString(2 * cm, y, "CPF:")
    c.setFont("Helvetica", 10)
    c.drawString(4 * cm, y, cpf)
    y -= 0.5 * cm
    c.setFont("Helvetica-Bold", 10)
    c.drawString(2 * cm, y, "Agencia/Conta:")
    c.setFont("Helvetica", 10)
    c.drawString(5 * cm, y, f"{agency} / {account_number}")

    # ─── Tabela genérica ou layout dedicado (regex dos parsers E2) ───
    y -= 1.2 * cm
    if bank == "btgpactual":
        y, _ = _draw_btgpactual_movimentacao(c, width, height, y, period, transactions)
    elif bank == "rico":
        rico_digits = "".join(ch for ch in account_number if ch.isdigit()) or "1234567890"
        y, _ = _draw_rico_extrato(c, width, height, y, period, transactions, rico_digits)
    elif bank == "wise":
        y, _ = _draw_wise_extrato(c, width, height, y, period, transactions)
    elif bank == "picpay":
        y, _ = _draw_picpay_extrato(c, width, height, y, period, transactions, account_number)
    elif bank == "bankofamerica":
        y, _ = _draw_bankofamerica_extrato(
            c, width, height, y, period, transactions, account_number
        )
    elif bank == "santander":
        y, _ = _draw_santander_extrato(
            c, width, height, y, period, transactions, agency, account_number
        )
    elif bank == "itau":
        y, _ = _draw_itau_extrato(c, width, height, y, period, transactions, account_number)
    elif bank == "caixa":
        y, _ = _draw_caixa_extrato(
            c, width, height, y, period, transactions, agency, account_number
        )
    else:
        c.setFont("Helvetica-Bold", 9)
        c.drawString(2 * cm, y, "Data")
        c.drawString(4 * cm, y, "Descricao")
        c.drawString(13 * cm, y, "Valor (R$)")
        c.drawString(16.5 * cm, y, "Saldo (R$)")
        c.line(2 * cm, y - 0.1 * cm, width - 2 * cm, y - 0.1 * cm)

        y -= 0.5 * cm
        c.setFont("Courier", 9)
        running_balance = 0.0
        total_credits = 0.0
        total_debits = 0.0
        for tx in transactions:
            if y < 3 * cm:
                c.showPage()
                y = height - 2 * cm
                c.setFont("Courier", 9)
            amount = float(tx.get("amount", 0))
            running_balance = float(tx.get("balance", running_balance + amount))
            if amount >= 0:
                total_credits += amount
            else:
                total_debits += amount
            c.drawString(2 * cm, y, str(tx.get("date", "")))
            desc = str(tx.get("description", ""))[:50]
            c.drawString(4 * cm, y, desc)
            c.drawRightString(15.5 * cm, y, _format_brl(amount))
            c.drawRightString(width - 2 * cm, y, _format_brl(running_balance))
            y -= 0.4 * cm

        # ─── Totais ───
        y -= 0.3 * cm
        c.line(2 * cm, y, width - 2 * cm, y)
        y -= 0.5 * cm
        c.setFont("Helvetica-Bold", 9)
        c.drawString(2 * cm, y, "Total Creditos:")
        c.drawRightString(15.5 * cm, y, _format_brl(total_credits))
        y -= 0.4 * cm
        c.drawString(2 * cm, y, "Total Debitos:")
        c.drawRightString(15.5 * cm, y, _format_brl(total_debits))
        y -= 0.4 * cm
        c.drawString(2 * cm, y, "Saldo Final:")
        c.drawRightString(15.5 * cm, y, _format_brl(running_balance))

    # ─── Footer ───
    c.setFont("Helvetica", 7)
    c.drawString(2 * cm, 1.5 * cm,
                 f"Documento sintetico de teste. Nao reflete dados reais. "
                 f"Gerado em {creation_date.isoformat()} para fins de teste automatizado.")
    c.drawRightString(width - 2 * cm, 1.5 * cm, "Pagina 1 de 1")

    c.showPage()
    c.save()
    return buf.getvalue()


def write_statement_pdf(
    path: str | Path,
    bank: BankCode,
    kind: DocKind = "extrato",
    **kwargs,
) -> Path:
    """Escreve PDF gerado em `path` e retorna o Path."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(generate_statement(bank, kind, **kwargs))
    return p


__all__ = [
    "BankCode",
    "DocKind",
    "Transaction",
    "generate_statement",
    "write_statement_pdf",
]
