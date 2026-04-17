#!/usr/bin/env python3
"""Tests for E3 deduplication logic."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.e3_reconcile import (
    transaction_signature,
    deduplicate_transactions,
    _normalize_description_for_dedup,
    normalize_periodo_in_extract,
)


class TestTransactionSignature:
    def test_basic_signature(self):
        txn = {"data": "2026-01-15", "valor": 100.50, "descricao": "PIX SENT"}
        sig = transaction_signature(txn)
        assert sig[0] == "2026-01-15"
        assert sig[1] == 100.50
        assert "PIX" in sig[2]

    def test_float_rounding(self):
        """Float values should be rounded to 2 decimal places in signatures."""
        txn1 = {"data": "2026-01-15", "valor": 100.0000001, "descricao": "TEST"}
        txn2 = {"data": "2026-01-15", "valor": 100.00, "descricao": "TEST"}
        assert transaction_signature(txn1) == transaction_signature(txn2)

    def test_missing_fields(self):
        txn = {}
        sig = transaction_signature(txn)
        assert sig[0] == ""
        assert sig[1] == 0

    def test_none_valor(self):
        txn = {"data": "2026-01-15", "valor": None, "descricao": "TEST"}
        sig = transaction_signature(txn)
        assert sig[1] is None


class TestNormalizeDescription:
    def test_em_dash_suffix_removed(self):
        assert "TRANSF" not in _normalize_description_for_dedup(
            "Pix enviado para João — TRANSF ENVIADA PIX"
        ) or _normalize_description_for_dedup(
            "Pix enviado para João — TRANSF ENVIADA PIX"
        ) == _normalize_description_for_dedup(
            "Pix enviado para João"
        )

    def test_uppercase_and_whitespace_collapse(self):
        result = _normalize_description_for_dedup("  pix  enviado  ")
        assert result == "PIX ENVIADO"

    def test_non_ascii_stripped(self):
        result = _normalize_description_for_dedup("Veículo João")
        assert "í" not in result
        assert "ã" not in result


class TestDeduplicateTransactions:
    def test_no_duplicates(self):
        txns = [
            ({"data": "2026-01-15", "valor": 100.0, "descricao": "A"}, "file1.json"),
            ({"data": "2026-01-16", "valor": 200.0, "descricao": "B"}, "file1.json"),
        ]
        result, removed, _details = deduplicate_transactions(txns)
        assert len(result) == 2
        assert removed == 0

    def test_cross_file_duplicate_removed(self):
        txn = {"data": "2026-01-15", "valor": 100.0, "descricao": "SAME"}
        txns = [
            (dict(txn), "file1.json"),
            (dict(txn), "file2.json"),
        ]
        result, removed, _details = deduplicate_transactions(txns)
        assert len(result) == 1
        assert removed == 1

    def test_intra_file_duplicates_kept(self):
        txn = {"data": "2026-01-15", "valor": 68.55, "descricao": "AMAZON"}
        txns = [
            (dict(txn), "file1.json"),
            (dict(txn), "file1.json"),
        ]
        result, removed, _details = deduplicate_transactions(txns)
        assert len(result) == 2
        assert removed == 0

    def test_cross_file_keeps_first_source(self):
        """When multiple files have same sig, keep from lexicographically first file."""
        txn_a = {"data": "2026-01-15", "valor": 100.0, "descricao": "SAME", "source_marker": "a"}
        txn_b = {"data": "2026-01-15", "valor": 100.0, "descricao": "SAME", "source_marker": "b"}
        txns = [
            (txn_b, "b_file.json"),
            (txn_a, "a_file.json"),
        ]
        result, removed, _details = deduplicate_transactions(txns)
        assert len(result) == 1
        assert result[0].get("source_marker") == "a"
        assert removed == 1

    def test_empty_input(self):
        result, removed, _details = deduplicate_transactions([])
        assert result == []
        assert removed == 0


class TestNormalizePeriodo:
    """E2-llm wrote periodo as YYYYMM string — E3 must coerce before .get(inicio)."""

    def test_yyyymm_string_to_range(self):
        d = {"tipo": "extrato", "periodo": "202412", "transacoes": []}
        normalize_periodo_in_extract(d)
        assert d["periodo"]["inicio"] == "2024-12-01"
        assert d["periodo"]["fim"] == "2024-12-31"

    def test_dict_unchanged(self):
        d = {
            "periodo": {"inicio": "2024-01-01", "fim": "2024-01-31"},
            "transacoes": [],
        }
        normalize_periodo_in_extract(d)
        assert d["periodo"]["inicio"] == "2024-01-01"

    def test_iso_date_string(self):
        d = {"periodo": "2024-06-15", "transacoes": []}
        normalize_periodo_in_extract(d)
        assert d["periodo"]["inicio"] == "2024-06-15"
        assert d["periodo"]["fim"] == "2024-06-15"
