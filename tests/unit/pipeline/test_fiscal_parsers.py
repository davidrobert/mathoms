"""Tests para fiscal_parsers — DB row ↔ FiscalParameters ↔ legacy JSON (A7.2b · ADR-135)."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.adapters.fiscal_parsers import (  # noqa: E402
    fiscal_payload_to_dataclass,
    fiscal_row_to_payload,
    legacy_json_to_fiscal,
)
from pipeline.domain.types.config import FiscalParameters, IRPFBracket  # noqa: E402


@dataclass
class _StubRow:
    year: int
    ir_brackets: list
    pgbl_limit_brl_cents: int
    inss_ceiling_brl_cents: int
    lucro_presumido_aliquota: Decimal
    effective_from: date | None
    effective_to: date | None
    source: str


def _stub_row() -> _StubRow:
    return _StubRow(
        year=2025,
        ir_brackets=[
            {"upper_brl_cents": 2696320, "aliquota_pct": "0.0", "deducao_brl_cents": 0},
            {"upper_brl_cents": None, "aliquota_pct": "27.5", "deducao_brl_cents": 0},
        ],
        pgbl_limit_brl_cents=0,
        inss_ceiling_brl_cents=0,
        lucro_presumido_aliquota=Decimal("0.32"),
        effective_from=date(2025, 1, 1),
        effective_to=date(2025, 12, 31),
        source="test-source",
    )


# ---------------------------------------------------------------------------
# fiscal_row_to_payload
# ---------------------------------------------------------------------------


class TestRowToPayload:
    def test_serializes_to_json_safe_dict(self):
        payload = fiscal_row_to_payload(_stub_row())
        assert payload["year"] == 2025
        # Decimal vira string (JSON-safe)
        assert payload["lucro_presumido_aliquota"] == "0.32"
        # Datas vão como ISO
        assert payload["effective_from"] == "2025-01-01"
        assert payload["effective_to"] == "2025-12-31"

    def test_handles_open_ended_effective_to(self):
        row = _stub_row()
        row.effective_to = None
        payload = fiscal_row_to_payload(row)
        assert payload["effective_to"] is None


# ---------------------------------------------------------------------------
# fiscal_payload_to_dataclass
# ---------------------------------------------------------------------------


class TestPayloadToDataclass:
    def test_roundtrip(self):
        row = _stub_row()
        payload = fiscal_row_to_payload(row)
        fp = fiscal_payload_to_dataclass(payload)
        assert isinstance(fp, FiscalParameters)
        assert fp.year == row.year
        assert fp.lucro_presumido_aliquota == row.lucro_presumido_aliquota
        assert fp.effective_from == row.effective_from
        assert fp.effective_to == row.effective_to

    def test_brackets_are_typed(self):
        fp = fiscal_payload_to_dataclass(fiscal_row_to_payload(_stub_row()))
        assert all(isinstance(b, IRPFBracket) for b in fp.ir_brackets)
        assert fp.ir_brackets[-1].upper_brl_cents is None
        assert fp.ir_brackets[-1].aliquota_pct == Decimal("27.5")

    def test_handles_missing_optional_fields(self):
        fp = fiscal_payload_to_dataclass({"year": 2030})
        assert fp.year == 2030
        assert fp.ir_brackets == ()
        assert fp.lucro_presumido_aliquota == Decimal("0")


# ---------------------------------------------------------------------------
# legacy_json_to_fiscal — bridge para FileConfigStore
# ---------------------------------------------------------------------------


class TestLegacyJsonToFiscal:
    def test_converts_full_json_shape(self):
        raw = {
            "lucro_presumido": {"percentual_servicos_pct": 32.0},
            "pgbl": {"limite_deducao_pct": 12.0},
            "irpf_tabela_progressiva": {
                "faixas": [
                    {"limite_anual": 26963.20, "aliquota_pct": 0.0},
                    {"limite_anual": None, "aliquota_pct": 27.5},
                ]
            },
        }
        fp = legacy_json_to_fiscal(raw, year=2025)
        assert fp.year == 2025
        assert fp.lucro_presumido_aliquota == Decimal("0.32")
        assert len(fp.ir_brackets) == 2
        # 26963.20 * 100 = 2696320 cents
        assert fp.ir_brackets[0].upper_brl_cents == 2696320
        assert fp.ir_brackets[1].upper_brl_cents is None
        assert fp.effective_from == date(2025, 1, 1)
        assert fp.effective_to == date(2025, 12, 31)

    def test_empty_dict_returns_zero_defaults(self):
        fp = legacy_json_to_fiscal({}, year=2025)
        assert fp.year == 2025
        assert fp.ir_brackets == ()
        assert fp.lucro_presumido_aliquota == Decimal("0")

    def test_source_label_traceable(self):
        fp = legacy_json_to_fiscal({}, year=2025, source="custom-bridge")
        assert fp.source == "custom-bridge"

    def test_defaults_source_to_file_config_store_label(self):
        fp = legacy_json_to_fiscal({}, year=2025)
        assert "FileConfigStore" in fp.source

    def test_skips_non_dict_brackets(self):
        raw = {"irpf_tabela_progressiva": {"faixas": ["bad", None, 42]}}
        fp = legacy_json_to_fiscal(raw, year=2025)
        assert fp.ir_brackets == ()
