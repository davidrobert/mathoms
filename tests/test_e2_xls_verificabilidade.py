#!/usr/bin/env python3
"""A39.l7 — parse_itau_xls e parse_santander_xls leem saldo_inicial (SALDO
ANTERIOR) e saldo_final de células independentes (não derivados) → declaram
conservacao_verificavel para o gate HARD da ADR-342 graduar. Wise/Rico ficam de
fora (saldo derivado tautológico). Fixtures sintéticas via xlwt (dev-dep)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.e2.banks.itau import parse_itau_xls
from scripts.e2.banks.santander import parse_santander_xls
from scripts.e2.validation import conservation_gap_cents, validate_extrato_result
from tests.fixtures.pdf.xls import generate_itau_xls, generate_santander_xls

_TXS = [
    {"date": "2025-01-05", "description": "Mercado", "amount": -450.0},
    {"date": "2025-01-10", "description": "Salario", "amount": 5000.0},
    {"date": "2025-01-20", "description": "Aluguel", "amount": -1800.0},
]

# O builder sintético do Santander escreve as linhas em ordem cronológica, mas
# parse_santander_xls reverte (o layout real é newest-first) → com múltiplas tx o
# saldo_final da fixture cairia na linha errada (limitação do builder, não do
# parser: os XLS reais fecham em cents). 1 tx torna a ordem irrelevante.
_TXS_SANT = [{"date": "2025-01-05", "description": "Mercado", "amount": -450.0}]


def _write(tmp_path: Path, name: str, data: bytes) -> Path:
    p = tmp_path / name
    p.write_bytes(data)
    return p


def test_itau_xls_limpo_declara_verificavel_e_fecha(tmp_path: Path) -> None:
    p = _write(
        tmp_path,
        "itau_extratoconta_202501_202501-0_original.xls",
        generate_itau_xls("2025-01", _TXS),
    )
    result = parse_itau_xls(p, p.name)
    assert result["conservacao_verificavel"] is True
    assert conservation_gap_cents(result) == 0
    validate_extrato_result(result, p, is_csv=True)
    assert "requires_llm_fallback" not in result


def test_itau_xls_gap_escala_honesto(tmp_path: Path) -> None:
    p = _write(
        tmp_path,
        "itau_extratoconta_202501_202501-0_original.xls",
        generate_itau_xls("2025-01", _TXS),
    )
    result = parse_itau_xls(p, p.name)
    assert result["conservacao_verificavel"] is True
    result["saldo_final"] = (result["saldo_final"] or 0) + 1000.0  # injeta gap material
    validate_extrato_result(result, p, is_csv=True)
    assert result["requires_llm_fallback"] is True


def test_santander_xls_limpo_declara_verificavel_e_fecha(tmp_path: Path) -> None:
    p = _write(
        tmp_path,
        "santander_extratoconta_202501_202501-0_original.xls",
        generate_santander_xls("2025-01", _TXS_SANT),
    )
    result = parse_santander_xls(p, p.name)
    assert result["conservacao_verificavel"] is True
    assert conservation_gap_cents(result) == 0
    validate_extrato_result(result, p, is_csv=True)
    assert "requires_llm_fallback" not in result


def test_santander_xls_gap_escala_honesto(tmp_path: Path) -> None:
    p = _write(
        tmp_path,
        "santander_extratoconta_202501_202501-0_original.xls",
        generate_santander_xls("2025-01", _TXS_SANT),
    )
    result = parse_santander_xls(p, p.name)
    assert result["conservacao_verificavel"] is True
    result["saldo_final"] = (result["saldo_final"] or 0) + 1000.0
    validate_extrato_result(result, p, is_csv=True)
    assert result["requires_llm_fallback"] is True
