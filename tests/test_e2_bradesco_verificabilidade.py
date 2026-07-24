#!/usr/bin/env python3
"""A39.l5 — parse_bradesco lê saldo_inicial (SALDO ANTERIOR) e saldo_final (linha
Total) de células observadas → declara conservacao_verificavel. Conservação que
não fecha (ex.: conta-corrente com sweep Invest Fácil cujas tx não reconciliam)
escala honesto em vez de WARN silencioso.

Diagnóstico do corpus (2026-07-23): o saldo R$1,00 de #f658 é REAL (conta com
varredura automática p/ Invest Fácil: créditos == débitos, saldo fica em R$1),
não um default espúrio. O defeito é de CAPTURA de transação do sweep (Σtx não
reconcilia) — a correção da captura é follow-up; esta lane garante que o doc
escala em vez de silenciar. Fixture sintética PII-zero."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.e2.banks.bradesco import parse_bradesco
from scripts.e2.validation import conservation_gap_cents, validate_extrato_result
from tests.fixtures.pdf_generator import generate_statement

_TX = [
    {"date": "2026-04-05", "description": "Mercado Sintetico", "amount": -250.50},
    {"date": "2026-04-10", "description": "Pagto Folha", "amount": 1250.00},
    {"date": "2026-04-20", "description": "Aluguel", "amount": -1800.00},
]


def _bradesco_pdf(tmp_path: Path) -> Path:
    p = tmp_path / "bradesco_extratoconta_202604_golden.pdf"
    p.write_bytes(
        generate_statement(
            "bradesco",
            "extrato",
            period="2026-04",
            transactions=_TX,
            account_holder="Titular Golden",
            agency="3221",
            account_number="77113-9",
        )
    )
    return p


def test_bradesco_limpo_declara_verificavel_e_fecha(tmp_path: Path) -> None:
    p = _bradesco_pdf(tmp_path)
    result = parse_bradesco(p, p.name)
    assert result["conservacao_verificavel"] is True
    assert conservation_gap_cents(result) == 0
    validate_extrato_result(result, p)
    assert "requires_llm_fallback" not in result


def test_bradesco_gap_escala_honesto(tmp_path: Path) -> None:
    p = _bradesco_pdf(tmp_path)
    result = parse_bradesco(p, p.name)
    assert result["conservacao_verificavel"] is True
    result["saldo_final"] = (result["saldo_final"] or 0) + 5000.0  # injeta gap
    validate_extrato_result(result, p)
    assert result["requires_llm_fallback"] is True
