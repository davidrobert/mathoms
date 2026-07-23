"""A38.l12 — parsers determinísticos de CDB em PDF (Itaú movimentação + Santander detalhes).

Emitem `tipo="cdbresumo"` (E4 seleciona por tipo; `cdbdetalhes` sumiria) +
`posicoes`; checksum Σ posições == total declarado escala em mismatch (ADR-342).
"""

from __future__ import annotations

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas

from scripts.e2.banks.itau import parse_itau_cdb_pdf
from scripts.e2.banks.santander import parse_santander_cdb_pdf


def _pdf(path, lines: list[str]) -> None:
    c = canvas.Canvas(str(path), pagesize=A4)
    _, height = A4
    y = height - 2 * cm
    c.setFont("Helvetica", 9)
    for line in lines:
        c.drawString(2 * cm, y, line)
        y -= 0.5 * cm
    c.save()


_ITAU_CDB = [
    "Extrato de movimentação mensal - CDB-DI",
    "Nome: FULANO DA SILVA",
    "Período: 01/07/2026 à 22/07/2026",
    "30/06/2026 SALDO ANTERIOR 100.000,00",
    "22/07/2026 SALDO FINAL 124.940,17",
    "Posição em 22/07/2026:",
    "123456789012 16/10/2029 11/11/2024 100.000,00 100,00 123.894,72 124.940,17 24,94",
]

_SANT_CDB = [
    "DETALHES DO INVESTIMENTO",
    "CDB Valor total (R$) : 312.072,26 Valores Referentes a : 22/07/2026",
    "CDB DI SANTANDER Valor Total : R$ 143.248,51 Disponível para Resgate : R$ 138.304,04",
    "Você possui 1 contrato neste investimento",
    "CDB PROG SANTANDER Valor Total : R$ 168.823,75 Disponível para Resgate : R$ 160.000,00",
    "Você possui 1 contrato neste investimento",
]


def test_itau_cdb_pdf_emite_cdbresumo_e_posicao(tmp_path) -> None:
    path = tmp_path / "itau_cdbdetalhes_202607-0_original.pdf"
    _pdf(path, _ITAU_CDB)
    r = parse_itau_cdb_pdf(path, path.name)
    assert r["tipo"] == "cdbresumo"  # NUNCA cdbdetalhes (sumiria no E4)
    assert not r.get("requires_llm_fallback")
    assert len(r["posicoes"]) == 1
    assert r["posicoes"][0]["nome"] == "CDB-DI"
    assert r["posicoes"][0]["valor_atual"] == 124940.17  # == SALDO FINAL


def test_santander_cdb_pdf_checksum_soma_bate_total(tmp_path) -> None:
    path = tmp_path / "santander_cdbdetalhes_202607-0_original.pdf"
    _pdf(path, _SANT_CDB)
    r = parse_santander_cdb_pdf(path, path.name)
    assert r["tipo"] == "cdbresumo"
    assert len(r["posicoes"]) == 2
    assert round(sum(p["valor_atual"] for p in r["posicoes"]), 2) == 312072.26
    assert not r.get("requires_llm_fallback")  # Σ == total declarado → não escala


def test_santander_cdb_pdf_checksum_mismatch_escala(tmp_path) -> None:
    """Total declarado ≠ Σ posições ⇒ escala (ADR-342 §Emenda l12)."""
    bad = list(_SANT_CDB)
    bad[1] = "CDB Valor total (R$) : 999.999,99 Valores Referentes a : 22/07/2026"
    path = tmp_path / "santander_cdbdetalhes_202607-0_original.pdf"
    _pdf(path, bad)
    r = parse_santander_cdb_pdf(path, path.name)
    assert r["requires_llm_fallback"] is True
    assert r["escalation_reason"]["code"] == "extract.investment_sum_mismatch"


def test_cdb_pdf_vazio_escala(tmp_path) -> None:
    path = tmp_path / "santander_cdbdetalhes_202607-0_original.pdf"
    _pdf(path, ["DETALHES DO INVESTIMENTO", "nenhum produto"])
    r = parse_santander_cdb_pdf(path, path.name)
    assert r["requires_llm_fallback"] is True
    assert r["escalation_reason"]["code"] == "extract.empty_result"


def test_posicao_nao_passa_pelo_gate_de_transacao(tmp_path) -> None:
    """Guarda A38.l12: artefato de posição (cdbresumo, 0 transacoes) NÃO escala
    pelo gate de completude de transação (protege CDB PDF e xls/xlsx pós-l14)."""
    from pathlib import Path

    from scripts.e2.validation import validate_extrato_result

    result = {
        "tipo": "cdbresumo",
        "posicoes": [{"nome": "CDB", "valor_atual": 100.0}],
        "transacoes": [],
        "periodo": {"inicio": "2026-07-01", "fim": "2026-07-31"},
    }
    issues = validate_extrato_result(result, Path("santander_cdbresumo_202607-0_original.pdf"))
    assert "requires_llm_fallback" not in result
    assert not any("provável falha" in i for i in issues)
