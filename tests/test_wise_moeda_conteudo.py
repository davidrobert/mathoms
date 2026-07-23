"""A38.l6 — moeda do extrato Wise vem do CONTEÚDO, nunca de default silencioso."""

from __future__ import annotations

from pathlib import Path

from scripts.e2.banks import wise as wise_mod

_HEADER_USD = (
    "Wise Payments Ltd.\n"
    "Extrato em USD\n"
    "22 de julho de 2025 [GMT-03:00] - 22 de julho de 2026 [GMT-03:00]\n"
    "Titular da Conta Número da conta\n"
    "USD em 22 de julho de 2026 [GMT-03:00] 1.000,00 USD\n"
    "Descrição Entrada Saída Valor\n"
    "Cashback 10,00 1.000,00\n"
    "29 de julho de 2025 Transação\n"
)


class _FakePage:
    def __init__(self, text: str) -> None:
        self._text = text

    def extract_text(self) -> str:
        return self._text


class _FakePdf:
    def __init__(self, text: str) -> None:
        self.pages = [_FakePage(text)]

    def __enter__(self):
        return self

    def __exit__(self, *args) -> None:
        return None


def _patch_pdf(monkeypatch, text: str) -> None:
    monkeypatch.setattr(wise_mod.pdfplumber, "open", lambda _path: _FakePdf(text))


def test_moeda_usd_por_conteudo_mesmo_com_filename_sem_moeda(monkeypatch) -> None:
    """O caso do bug: nome canônico genérico `wise_extratoconta_...` tratava USD como BRL."""
    _patch_pdf(monkeypatch, _HEADER_USD)
    result = wise_mod.parse_wise(Path("x.pdf"), "wise_extratoconta_2025-0_original.pdf")
    assert result["moeda"] == "USD"
    assert result["tipo"] == "extratocontausd"
    assert result["periodo"] == {"inicio": "2025-07-22", "fim": "2026-07-22"}


def test_conteudo_vence_filename_divergente(monkeypatch) -> None:
    _patch_pdf(monkeypatch, _HEADER_USD.replace("Extrato em USD", "Extrato em BRL"))
    result = wise_mod.parse_wise(Path("x.pdf"), "wise_extratocontausd_2025-0_original.pdf")
    assert result["moeda"] == "BRL"
    assert result["tipo"] == "extratocontabrl"


def test_fallback_filename_quando_header_ausente(monkeypatch) -> None:
    _patch_pdf(monkeypatch, "Wise Payments Ltd.\nsem header de moeda\n")
    result = wise_mod.parse_wise(Path("x.pdf"), "wise_extratocontausd_2025-0_original.pdf")
    assert result["moeda"] == "USD"


def test_moeda_indeterminada_escala_nunca_default_brl(monkeypatch) -> None:
    _patch_pdf(monkeypatch, "Wise Payments Ltd.\nsem header de moeda\n")
    result = wise_mod.parse_wise(Path("x.pdf"), "wise_extratoconta_2025-0_original.pdf")
    assert result["requires_llm_fallback"] is True
    assert result["transacoes"] == []
    assert any("Moeda indeterminada" in n for n in result["notas"])
