"""Golden sintético PII-zero — o checksum de completude de fatura FECHA por
seção end-to-end (parser → gate), e uma linha perdida QUEBRA nomeando o balde.

Santander (A39.l3): `Σ(despesa_brasil) == "Total Despesas/Débitos no Brasil"`,
com pagamento/exterior FORA da soma. Itaú (A39.l8): `Σ(lancamentos_atuais) ==
"Total dos lançamentos atuais"` (nacional + internacional + IOF).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pipeline.domain.review_reason import ReviewReasonCode
from scripts.e2.banks.itau import parse_itau_fatura
from scripts.e2.banks.santander import parse_santander_unique
from scripts.e2.validation import _apply_fatura_checksum, validate_fatura_result

pytest.importorskip("pdfplumber")
pytest.importorskip("reportlab")

_MISMATCH = ReviewReasonCode.extract_fatura_total_mismatch.value

# despesa_brasil = 250,50 + 90,00 + 3,20(IOF) = 343,70; pagamento e exterior fora.
_SANT_TX = [
    {
        "date": "2026-04-03",
        "description": "DEB AUTOM DE FATURA",
        "amount": -500.00,
        "kind": "payment",
    },
    {"date": "2026-04-05", "description": "MERCADO GOLDEN", "amount": 250.50},
    {"date": "2026-04-12", "description": "FARMACIA GOLDEN", "amount": 90.00},
    {"date": "2026-04-19", "description": "CLOUD GOLDEN", "amount": 80.00, "usd": 15.00},
    {"description": "IOF DESPESA NO EXTERIOR", "amount": 3.20, "kind": "iof"},
]

# lancamentos_atuais = 250,50 + 90,00 + 80,00(intl) + 3,20(IOF) = 423,70.
_ITAU_TX = [
    {"date": "2026-04-05", "description": "MERCADO GOLDEN", "amount": 250.50},
    {"date": "2026-04-12", "description": "FARMACIA GOLDEN", "amount": 90.00},
    {"date": "2026-04-19", "description": "CLOUD GOLDEN", "amount": 80.00, "usd": 15.00},
    {"description": "Repasse de IOF", "amount": 3.20, "kind": "iof"},
]


def _santander_pdf(tmp_path: Path, transactions) -> Path:
    from tests.fixtures.pdf_generator import generate_statement

    p = tmp_path / "santander_faturaunique_202604.pdf"
    p.write_bytes(
        generate_statement(
            "santander",
            "fatura",
            period="2026-04",
            transactions=transactions,
            account_holder="TITULAR GOLDEN",
        )
    )
    return p


def _itau_pdf(tmp_path: Path, transactions) -> Path:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.pdfgen import canvas

    from tests.fixtures.pdf.itau import draw_itau_fatura

    p = tmp_path / "itau_fatura_202604.pdf"
    c = canvas.Canvas(str(p), pagesize=A4)
    w, h = A4
    draw_itau_fatura(c, w, h, h - 2 * cm, "2026-04", transactions)
    c.save()
    return p


def _warn_codes(result) -> set:
    return {w["code"] for w in result.get("warn_reasons", [])}


def _somas_por_escopo(result) -> dict:
    somas: dict = {}
    for t in result["transacoes"]:
        if t.get("escopo"):
            somas[t["escopo"]] = somas.get(t["escopo"], 0) + round(t["valor"] * 100)
    return somas


def test_santander_checksum_ambos_baldes_fecham(tmp_path):
    r = parse_santander_unique(
        _santander_pdf(tmp_path, _SANT_TX), "santander_faturaunique_202604.pdf"
    )
    validate_fatura_result(r, "santander_faturaunique_202604.pdf")

    # Lista: um signal por seção impressa (despesa_brasil + exterior) — l3-c3.
    sig = r["total_lancamentos_conferivel"]
    assert isinstance(sig, list)
    assert {s["escopo"]: s["valor_cents"] for s in sig} == {
        "despesa_brasil": 34370,
        "exterior": 8000,
    }
    somas = _somas_por_escopo(r)
    assert somas["despesa_brasil"] == 34370 and somas["exterior"] == 8000
    # pagamento fora dos baldes, negativo, tipo=pagamento p/ E3/E4
    pay = [t for t in r["transacoes"] if t.get("escopo") == "pagamento"][0]
    assert pay["valor"] < 0 and pay["tipo"] == "pagamento"
    assert _MISMATCH not in _warn_codes(r)  # ambos fecham → sem WARN


def test_santander_checksum_quebra_ao_perder_linha_brasil(tmp_path):
    r = parse_santander_unique(
        _santander_pdf(tmp_path, _SANT_TX), "santander_faturaunique_202604.pdf"
    )
    # perda silenciosa: some 1 linha despesa_brasil do detalhe, total impresso intacto
    r["transacoes"] = [t for t in r["transacoes"] if t["descricao"] != "MERCADO GOLDEN"]
    issues: list[str] = []
    _apply_fatura_checksum(r, issues)
    assert _MISMATCH in _warn_codes(r)
    assert any("despesa_brasil" in i for i in issues)  # nomeia o balde


def test_santander_checksum_quebra_ao_perder_exterior(tmp_path):
    # l3-c3: o balde exterior agora é verificado (antes só tagueado).
    r = parse_santander_unique(
        _santander_pdf(tmp_path, _SANT_TX), "santander_faturaunique_202604.pdf"
    )
    r["transacoes"] = [t for t in r["transacoes"] if t["descricao"] != "CLOUD GOLDEN"]
    issues: list[str] = []
    _apply_fatura_checksum(r, issues)
    assert _MISMATCH in _warn_codes(r)
    assert any("exterior" in i for i in issues)


def test_itau_checksum_lancamentos_atuais_fecha(tmp_path):
    r = parse_itau_fatura(_itau_pdf(tmp_path, _ITAU_TX), "itau_fatura_202604.pdf")
    validate_fatura_result(r, "itau_fatura_202604.pdf")

    assert r["total_lancamentos_conferivel"] == {
        "valor_cents": 42370,
        "escopo": "lancamentos_atuais",
    }
    tagged = [t for t in r["transacoes"] if t.get("escopo") == "lancamentos_atuais"]
    assert sum(round(t["valor"] * 100) for t in tagged) == 42370
    # IOF internacional capturado (senão abre em 3,20)
    assert any("IOF" in t["descricao"] for t in r["transacoes"])
    assert _MISMATCH not in _warn_codes(r)


def test_itau_checksum_quebra_ao_perder_iof(tmp_path):
    r = parse_itau_fatura(_itau_pdf(tmp_path, _ITAU_TX), "itau_fatura_202604.pdf")
    r["transacoes"] = [t for t in r["transacoes"] if "IOF" not in t["descricao"]]
    issues: list[str] = []
    _apply_fatura_checksum(r, issues)
    assert _MISMATCH in _warn_codes(r)
    assert any("lancamentos_atuais" in i for i in issues)
