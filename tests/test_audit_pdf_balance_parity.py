"""Unit tests para `dev/audit_pdf_balance_parity.py` — funções puras de paridade."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_AUDIT_PATH = Path(__file__).resolve().parent.parent / "dev" / "audit_pdf_balance_parity.py"
_spec = importlib.util.spec_from_file_location("audit_pdf_balance_parity", _AUDIT_PATH)
audit = importlib.util.module_from_spec(_spec)
sys.modules["audit_pdf_balance_parity"] = audit
_spec.loader.exec_module(audit)


def test_paridade_perfeita_nao_flagada():
    payload = {
        "saldo_inicial": 1000.0,
        "saldo_final": 1200.0,
        "transacoes": [
            {"valor": 500.0},
            {"valor": -300.0},
        ],
    }
    m = audit._compute_metrics(payload)
    assert m["diff"] == 0.0
    assert audit._classify(m, 50.0, 0.01) is None


def test_diff_acima_threshold_flaga():
    payload = {
        "saldo_inicial": 0.0,
        "saldo_final": -6012.17,
        "transacoes": [{"valor": -214320.20}],  # bug C6 — txs somam mais que delta
    }
    m = audit._compute_metrics(payload)
    assert m["diff"] is not None and abs(m["diff"]) > 200_000
    assert audit._classify(m, 50.0, 0.01) == "paridade_quebrada"


def test_saldo_ausente():
    m = audit._compute_metrics(
        {"saldo_inicial": None, "saldo_final": None, "transacoes": [{"valor": 100.0}]}
    )
    assert audit._classify(m, 50.0, 0.01) == "saldo_ausente"


def test_zero_transacoes_nao_flagado():
    m = audit._compute_metrics({"saldo_inicial": 0.0, "saldo_final": 0.0, "transacoes": []})
    assert audit._classify(m, 50.0, 0.01) is None


def test_diff_abaixo_threshold_absoluto_nao_flaga():
    payload = {"saldo_inicial": 0.0, "saldo_final": 1000.0, "transacoes": [{"valor": 1030.0}]}
    m = audit._compute_metrics(payload)
    assert abs(m["diff"]) == 30.0  # < 50
    assert audit._classify(m, 50.0, 0.01) is None


def test_diff_abaixo_threshold_pct_nao_flaga():
    """Volume R$ 100k, diff R$ 200 = 0,2% < 1%."""
    payload = {"saldo_inicial": 0.0, "saldo_final": 100_200.0, "transacoes": [{"valor": 100_000.0}]}
    m = audit._compute_metrics(payload)
    assert audit._classify(m, 50.0, 0.01) is None


def test_fatura_detectada_por_tipo():
    assert audit._is_fatura({"tipo": "faturacarbon"}, "c6bank_x") is True
    assert audit._is_fatura({"tipo": "faturaunique"}, "santander_x") is True


def test_fatura_detectada_por_artifact_key():
    assert audit._is_fatura({}, "c6bank_faturacarbon_202510_210006") is True
    assert audit._is_fatura({}, "santander_fatura_x") is True


def test_extrato_nao_eh_fatura():
    assert audit._is_fatura({"tipo": "extratoconta"}, "c6bank_extratoconta_202504_202604") is False
