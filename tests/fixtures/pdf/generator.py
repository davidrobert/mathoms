"""Synthetic PDF generator — F6.5 (sub-fase 6.5F.12).

Gera fatura/extrato sintético por banco para uso em tests (E2E + integration).
Substitui qualquer PDF real em ``tests/``, eliminando risco LGPD (ADR-063).

# Por que reportlab e não weasyprint?
- Sem dependência de Cairo/Pango (instalação trivial em Linux/macOS/Windows).
- Determinístico: PDF gerado byte-a-byte idêntico para o mesmo input.
- Pequeno: deps em <5MB.

# Determinismo
- Datas pinned via parâmetro ``creation_date`` (default 2026-04-15T12:00:00Z).
- Fonts: usar apenas Helvetica/Courier (built-in PDF, sem subset variável).
- Sem timestamps/IDs aleatórios — todos derivados do seed.
- ``setProducer`` desabilitado para não vazar versão da lib em diff de bytes.

# Bancos cobertos (14 — alinhado com ``config/institutions.json`` +
# ``scripts/e2/registry.py``)
# Layout dedicado: C6, Bradesco, BTG, Rico, Wise, PicPay, Bank of America,
# Santander, Itaú, Caixa, Quinto Andar — ``draw_*`` nos módulos irmãos.
# Demais: tabela genérica até evolução incremental.
- Brasileiros: c6bank, itau, santander, bradesco, btgpactual, rico, picpay, caixa
- Internacionais: bankofamerica, wise, binance
- Outros: quintoandar (aluguel), receitafederal (IRPF), einstein (saúde)

# CPFs e nomes
NUNCA usar CPFs reais. Os defaults aqui são ``000.000.000-00`` (placeholder) e
nomes obviamente fictícios. Tests que precisam CPF válido mod-11 devem usar
o gerador determinístico em ``tests/utils/cpf.py`` e passar explicitamente.
"""

from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Literal, TypedDict

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.pdfgen import canvas
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "tests/fixtures/pdf/generator.py requer reportlab. "
        "Instale com `pip install reportlab` ou via requirements-dev.txt."
    ) from exc

from tests.fixtures.pdf.bankofamerica import draw_bankofamerica_extrato
from tests.fixtures.pdf.bradesco import draw_bradesco_extrato
from tests.fixtures.pdf.btg import draw_btgpactual_movimentacao
from tests.fixtures.pdf.c6 import draw_c6_carbon_fatura, draw_c6_extrato
from tests.fixtures.pdf.caixa import draw_caixa_extrato
from tests.fixtures.pdf.formatters import format_brl
from tests.fixtures.pdf.itau import draw_itau_extrato, draw_itau_paoacucar_fatura
from tests.fixtures.pdf.picpay import draw_picpay_extrato
from tests.fixtures.pdf.quintoandar import draw_quintoandar_fatura
from tests.fixtures.pdf.rico import draw_rico_extrato
from tests.fixtures.pdf.santander import (
    draw_santander_extrato,
    draw_santander_unique_fatura,
)
from tests.fixtures.pdf.wise import draw_wise_extrato

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


def _draw_header(c, width, height, bank: str, kind: str, period: str) -> float:
    label = _BANK_LABELS[bank]
    c.setFont("Helvetica-Bold", 14)
    c.drawString(2 * cm, height - 2 * cm, label["name"])
    c.setFont("Helvetica", 8)
    c.drawString(2 * cm, height - 2.5 * cm, f"CNPJ: {label['cnpj']}")
    c.drawString(2 * cm, height - 2.9 * cm, f"Periodo: {period}")
    c.drawString(
        width - 6 * cm,
        height - 2 * cm,
        f"{'Extrato de Conta' if kind == 'extrato' else 'Fatura de Cartao'}",
    )
    return height - 4 * cm


def _draw_account_block(c, y, account_holder, cpf, agency, account_number) -> float:
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
    return y - 1.2 * cm


def _draw_generic_table(c, width, height, y, transactions) -> tuple[float, float]:
    """Tabela genérica para bancos sem layout dedicado."""
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
        c.drawRightString(15.5 * cm, y, format_brl(amount))
        c.drawRightString(width - 2 * cm, y, format_brl(running_balance))
        y -= 0.4 * cm

    # ─── Totais ───
    y -= 0.3 * cm
    c.line(2 * cm, y, width - 2 * cm, y)
    y -= 0.5 * cm
    c.setFont("Helvetica-Bold", 9)
    c.drawString(2 * cm, y, "Total Creditos:")
    c.drawRightString(15.5 * cm, y, format_brl(total_credits))
    y -= 0.4 * cm
    c.drawString(2 * cm, y, "Total Debitos:")
    c.drawRightString(15.5 * cm, y, format_brl(total_debits))
    y -= 0.4 * cm
    c.drawString(2 * cm, y, "Saldo Final:")
    c.drawRightString(15.5 * cm, y, format_brl(running_balance))
    return y, running_balance


def _draw_bank_body(
    c,
    width,
    height,
    y,
    bank,
    period,
    transactions,
    account_number,
    agency,
    *,
    kind="extrato",
    account_holder="Founder Teste",
) -> tuple[float, float]:
    """Despacha para o layout dedicado do banco/kind; fallback: tabela genérica."""
    if kind == "fatura":
        # Faturas de cartão com layout dedicado (A24.l7 — corpus do flip strict).
        if bank == "c6bank":
            return draw_c6_carbon_fatura(c, width, height, y, period, transactions, account_holder)
        if bank == "itau":
            return draw_itau_paoacucar_fatura(c, width, height, y, period, transactions)
        if bank == "santander":
            return draw_santander_unique_fatura(
                c, width, height, y, period, transactions, account_holder
            )
    if bank == "c6bank":
        return draw_c6_extrato(c, width, height, y, period, transactions, account_number)
    if bank == "bradesco":
        return draw_bradesco_extrato(
            c,
            width,
            height,
            y,
            period,
            transactions,
            agency,
            account_number,
        )
    if bank == "btgpactual":
        return draw_btgpactual_movimentacao(c, width, height, y, period, transactions)
    if bank == "rico":
        rico_digits = "".join(ch for ch in account_number if ch.isdigit()) or "1234567890"
        return draw_rico_extrato(c, width, height, y, period, transactions, rico_digits)
    if bank == "wise":
        return draw_wise_extrato(c, width, height, y, period, transactions)
    if bank == "picpay":
        return draw_picpay_extrato(c, width, height, y, period, transactions, account_number)
    if bank == "bankofamerica":
        return draw_bankofamerica_extrato(
            c,
            width,
            height,
            y,
            period,
            transactions,
            account_number,
        )
    if bank == "santander":
        return draw_santander_extrato(
            c,
            width,
            height,
            y,
            period,
            transactions,
            agency,
            account_number,
        )
    if bank == "itau":
        return draw_itau_extrato(c, width, height, y, period, transactions, account_number)
    if bank == "caixa":
        return draw_caixa_extrato(
            c,
            width,
            height,
            y,
            period,
            transactions,
            agency,
            account_number,
        )
    if bank == "quintoandar":
        return draw_quintoandar_fatura(c, width, height, y, period, transactions)
    return _draw_generic_table(c, width, height, y, transactions)


def _draw_footer(c, width, creation_date: datetime) -> None:
    c.setFont("Helvetica", 7)
    c.drawString(
        2 * cm,
        1.5 * cm,
        f"Documento sintetico de teste. Nao reflete dados reais. "
        f"Gerado em {creation_date.isoformat()} para fins de teste automatizado.",
    )
    c.drawRightString(width - 2 * cm, 1.5 * cm, "Pagina 1 de 1")


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

    O conteúdo é simples (1 página A4) com texto extraível. Layouts dedicados
    vivem em ``tests/fixtures/pdf/<banco>.py``; demais caem numa tabela
    genérica (ISO nas linhas) até evolução incremental.
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

    y = _draw_header(c, width, height, bank, kind, period)
    y = _draw_account_block(c, y, account_holder, cpf, agency, account_number)
    _draw_bank_body(
        c,
        width,
        height,
        y,
        bank,
        period,
        transactions,
        account_number,
        agency,
        kind=kind,
        account_holder=account_holder,
    )

    _draw_footer(c, width, creation_date)
    c.showPage()
    c.save()
    return buf.getvalue()


def write_statement_pdf(
    path: str | Path,
    bank: BankCode,
    kind: DocKind = "extrato",
    **kwargs,
) -> Path:
    """Escreve PDF gerado em ``path`` e retorna o Path."""
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
