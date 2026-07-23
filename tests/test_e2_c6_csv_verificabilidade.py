#!/usr/bin/env python3
"""A39.l2 — parse_c6bank_csv declara conservacao_verificavel (semântica de saldo
ancorada, não tautológica) → o gate HARD da ADR-342 escala perda silenciosa em
vez de só WARN. Fixtures sintéticas PII-zero."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.e2.banks.c6bank import parse_c6bank_csv
from scripts.e2.validation import conservation_gap_cents, validate_extrato_result

_HEADER = (
    "EXTRATO DE CONTA CORRENTE C6 BANK\n\n"
    "Agência: 1 / Conta: 987654321\n"
    "Extrato gerado em 31/01/2025 - as 12:00:00\n\n"
    "Extrato de 01/01/2025 a 31/01/2025\n\n"
    "Data Lançamento,Data Contábil,Título,Descrição,Entrada,Saída,Saldo\n"
)

# Fecha: saldo_inicial (âncora 5000 − 1ª tx 5000) = 0; Σtx = 4465; saldo_final = 4465.
_CSV_LIMPO = _HEADER + (
    "01/01/2025,01/01/2025,CRÉDITO,Salario,5000.00,,5000.00\n"
    "05/01/2025,05/01/2025,DÉBITO,Mercado,,450.00,4550.00\n"
    "28/01/2025,28/01/2025,DÉBITO,Restaurante,,85.00,4465.00\n"
)

# Row-drop: a coluna Saldo termina em 3665 mas Σ das tx fecha em 4465 (âncora 0)
# → ~R$800 de movimento não listado. gap = 0 + 4465 − 3665 = +800 ≠ 0.
_CSV_COM_GAP = _HEADER + (
    "01/01/2025,01/01/2025,CRÉDITO,Salario,5000.00,,5000.00\n"
    "05/01/2025,05/01/2025,DÉBITO,Mercado,,450.00,4550.00\n"
    "28/01/2025,28/01/2025,DÉBITO,Restaurante,,85.00,3665.00\n"
)


def _write(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "c6bank_extratoconta_202501_202501-0_original.csv"
    p.write_text(content, encoding="utf-8-sig")
    return p


def test_c6_csv_limpo_declara_verificavel_e_nao_escala(tmp_path: Path) -> None:
    p = _write(tmp_path, _CSV_LIMPO)
    result = parse_c6bank_csv(p, p.name)
    assert result["conservacao_verificavel"] is True
    assert conservation_gap_cents(result) == 0
    validate_extrato_result(result, p, is_csv=True)
    assert "requires_llm_fallback" not in result


def test_c6_csv_gap_material_escala_honesto(tmp_path: Path) -> None:
    p = _write(tmp_path, _CSV_COM_GAP)
    result = parse_c6bank_csv(p, p.name)
    assert result["conservacao_verificavel"] is True
    assert conservation_gap_cents(result) != 0
    validate_extrato_result(result, p, is_csv=True)
    assert result["requires_llm_fallback"] is True
