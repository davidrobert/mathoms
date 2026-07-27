"""Gate anti-silêncio (ADR-342 §Emenda A38.l14) — Wise reporta raw_rows_detected
do PRÓPRIO layout (2 linhas por tx: marcador "N de mês de AAAA Transação" + linha
de valor). Antes usava count_candidate_rows (exige data+valor na MESMA linha) → 0
p/ Wise, cegando o gate: falha de parse (0 tx com linhas reais) virava falsa
dormância. Validado no corpus 5@5.com (raw passou de 0 → n_tx: 31/7/31/17)."""

from __future__ import annotations

from scripts.e2.banks import wise as wmod
from scripts.e2.banks.wise import _count_wise_candidate_rows


def test_counts_transaction_markers() -> None:
    text = (
        "10 de janeiro de 2026 Transação\nMercado 100,00 500,00\n"
        "05 de janeiro de 2026 Transação\nSalario 200,00 400,00\n"
    )
    assert _count_wise_candidate_rows(text) == 2


def test_no_markers_is_zero() -> None:
    assert _count_wise_candidate_rows("saldo estável, sem movimentação no período") == 0


class _FakePdf:
    def __init__(self, text: str) -> None:
        self._text = text

    @property
    def pages(self):
        return [self]

    def extract_text(self) -> str:
        return self._text

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_parse_failure_not_silent(monkeypatch, tmp_path) -> None:
    """Marcador de tx presente mas linha de valor corrompida → 0 tx extraídas MAS
    raw_rows_detected=1 ⇒ o gate vê linha-candidata não-convertida (NÃO dormância)."""
    text = "Extrato em USD\n2 de janeiro de 2026 Transação\nLINHA CORROMPIDA SEM VALOR\n"
    monkeypatch.setattr(wmod.pdfplumber, "open", lambda _p: _FakePdf(text))
    path = tmp_path / "wise_extratoconta_202601_202601-0_original.pdf"
    path.write_bytes(b"%PDF-fake")

    result = wmod.parse_wise(path, path.name)
    assert len(result.get("transacoes") or []) == 0  # parse não converteu
    assert result["raw_rows_detected"] == 1  # mas há candidata → gate não trata como dormante
