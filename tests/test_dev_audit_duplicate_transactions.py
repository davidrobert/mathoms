"""Smoke tests para dev/audit_duplicate_transactions.py (ADR-248)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

_MODULE_PATH = Path(__file__).parent.parent / "dev" / "audit_duplicate_transactions.py"
_SPEC = importlib.util.spec_from_file_location("audit_duplicate_transactions", _MODULE_PATH)
assert _SPEC is not None and _SPEC.loader is not None
_module = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_module)


class TestForensicKey:
    def test_round_trips_cents(self):
        # 47208.77 deve gerar cents = 4720877 (sem float drift)
        tx = {"data": "2026-03-30", "valor": 47208.77, "descricao": "ARVO"}
        k = _module._forensic_key(tx)
        assert k == ("2026-03-30", 4720877, "arvo")

    def test_normalizes_descricao_to_lower(self):
        tx = {"data": "2026-01-01", "valor": 10.0, "descricao": "  PIX Recebido  "}
        k = _module._forensic_key(tx)
        assert k == ("2026-01-01", 1000, "pix recebido")

    def test_none_when_data_missing(self):
        assert _module._forensic_key({"valor": 10.0, "descricao": "X"}) is None

    def test_none_when_valor_missing(self):
        assert _module._forensic_key({"data": "2026-01-01", "descricao": "X"}) is None

    def test_none_when_descricao_empty(self):
        assert _module._forensic_key({"data": "2026-01-01", "valor": 10.0, "descricao": ""}) is None


class TestSummarize:
    def test_empty_index_returns_empty(self):
        assert _module._summarize({}) == []

    def test_filters_singletons(self):
        # Tx que aparece em 1 key só não é dup.
        index = {
            "ws1": {
                "run1": {
                    ("2026-01-01", 100, "x"): ["key_a"],
                }
            }
        }
        assert _module._summarize(index) == []

    def test_reports_dups(self):
        index = {
            "ws1": {
                "run1": {
                    ("2026-01-01", 100, "x"): ["key_a", "key_b"],  # 1 dup
                    ("2026-01-02", 200, "y"): ["key_c", "key_d", "key_e"],  # 2 extras
                }
            }
        }
        out = _module._summarize(index)
        assert len(out) == 1
        entry = out[0]
        assert entry["workspace_id"] == "ws1"
        assert entry["pipeline_run_id"] == "run1"
        assert entry["dup_unique_txs"] == 2
        assert entry["total_extra_copies"] == 1 + 2  # extra copies = len-1 cada
        # sample ordenado por len(keys) desc → "y" com 3 keys vem antes de "x" com 2.
        assert entry["sample"][0]["descricao_lower"] == "y"
        assert entry["sample"][1]["descricao_lower"] == "x"
