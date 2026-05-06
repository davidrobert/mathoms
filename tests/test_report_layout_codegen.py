#!/usr/bin/env python3
"""Tests for dev/codegen_report_layout.py — ADR-076 · F0.2.5.

Valida que o YAML passa no schema, que codegen é determinístico,
e que TS e Pydantic gerados são sintáticamente válidos.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_CODEGEN_PY = ROOT / "dev" / "codegen_report_layout.py"

_spec = importlib.util.spec_from_file_location("codegen_report_layout", _CODEGEN_PY)
assert _spec and _spec.loader
codegen = importlib.util.module_from_spec(_spec)
sys.modules["codegen_report_layout"] = codegen
_spec.loader.exec_module(codegen)

YAML_PATH = codegen.YAML_PATH
SCHEMA_PATH = codegen.SCHEMA_PATH
TS_OUTPUT = codegen.TS_OUTPUT
PY_OUTPUT = codegen.PY_OUTPUT


@pytest.fixture(scope="module")
def layout() -> dict:
    return codegen.load_yaml()


class TestSchema:
    def test_schema_exists(self):
        assert SCHEMA_PATH.exists()

    def test_schema_is_valid_json(self):
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        assert "$schema" in schema
        assert "properties" in schema

    def test_yaml_validates_against_schema(self, layout):
        codegen.validate(layout)  # raises on failure


class TestCodegenYAML:
    def test_yaml_has_single_mode(self, layout):
        # ADR-151 — Modo Tático removido. ADR-168 (A8.4 PR4) — Modo USA removido.
        # Estratégico é o modo único.
        assert "estrategico" in layout
        assert "tatico" not in layout
        assert "usa" not in layout

    def test_version_is_string(self, layout):
        assert isinstance(layout["version"], str)

    def test_all_card_variants_valid(self, layout):
        allowed = {
            "highlight",
            "feature",
            "success",
            "warn",
            "critical",
            "primary",
            "neutral",
            "top-danger",
            "top-accent",
        }
        all_sections = layout["estrategico"]["sections"]
        for section in all_sections:
            for card in section.get("cards", []) or []:
                if "variant" in card:
                    assert (
                        card["variant"] in allowed
                    ), f"card {card['id']}: variant '{card['variant']}' not in design-tokens"

    def test_card_variants_match_design_tokens(self, layout):
        """Variantes usadas no YAML devem existir em design-tokens/tokens.json."""
        tokens = json.loads((ROOT / "design-tokens" / "tokens.json").read_text())
        allowed = set(tokens["card_variants"].keys())
        all_sections = layout["estrategico"]["sections"]
        used: set[str] = set()
        for section in all_sections:
            for card in section.get("cards", []) or []:
                if "variant" in card:
                    used.add(card["variant"])
        missing = used - allowed
        assert not missing, f"variantes no YAML mas ausentes em tokens.json: {missing}"


class TestCodegenOutputs:
    def test_build_returns_two_strings(self):
        ts, py = codegen.build()
        assert ts and py
        assert isinstance(ts, str)
        assert isinstance(py, str)

    def test_determinism(self):
        a_ts, a_py = codegen.build()
        b_ts, b_py = codegen.build()
        assert a_ts == b_ts
        assert a_py == b_py

    def test_ts_has_required_exports(self):
        ts, _ = codegen.build()
        for exp in [
            "export type CardVariant",
            "export type CardSize",
            "export type ReportMode",
            "export interface CardSpec",
            "export interface ChartSpec",
            "export interface SectionSpec",
            "export interface ReportLayout",
            "export const LAYOUT",
            "export const ALL_CARD_IDS",
            "export const ALL_CHART_IDS",
        ]:
            assert exp in ts, f"missing: {exp}"

    def test_py_has_required_exports(self):
        _, py = codegen.build()
        for exp in [
            "class CardSpec",
            "class ChartSpec",
            "class SectionSpec",
            "class ReportLayout",
            "LAYOUT_DICT",
            "LAYOUT: ReportLayout",
            "ALL_CARD_IDS",
            "ALL_CHART_IDS",
        ]:
            assert exp in py, f"missing: {exp}"


class TestGeneratedFilesOnDisk:
    def test_ts_file_exists_and_in_sync(self):
        assert TS_OUTPUT.exists(), (
            f"{TS_OUTPUT.relative_to(ROOT)} not generated — "
            "run `python3 dev/codegen_report_layout.py`"
        )
        expected_ts, _ = codegen.build()
        actual = TS_OUTPUT.read_text(encoding="utf-8")
        assert actual == expected_ts, "TS out of sync — run `python3 dev/codegen_report_layout.py`"

    def test_py_file_exists_and_in_sync(self):
        assert PY_OUTPUT.exists()
        _, expected_py = codegen.build()
        actual = PY_OUTPUT.read_text(encoding="utf-8")
        assert actual == expected_py

    def test_generated_init_exists(self):
        init = PY_OUTPUT.parent / "__init__.py"
        assert init.exists(), "backend/app/generated/__init__.py não foi criado"
