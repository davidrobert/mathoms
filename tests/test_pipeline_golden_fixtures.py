"""Golden fixtures em ``tests/fixtures/pipeline_golden/`` — validação contra schemas canônicos."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
_FIXTURES = _REPO / "tests" / "fixtures" / "pipeline_golden"
_SCHEMAS = _REPO / "config" / "schemas"


@pytest.mark.parametrize(
    "fixture_path,schema_name",
    [
        (_FIXTURES / "e2" / "minimal-extrato-2_extract.json", "e2_extract.schema.json"),
        (_FIXTURES / "e3" / "minimal-conta-3_reconciled.json", "e3_reconciled.schema.json"),
        (_FIXTURES / "e3" / "minimal-conta-com-despesa-3_reconciled.json", "e3_reconciled.schema.json"),
        (_FIXTURES / "e4" / "minimal-receitas-4_unified.json", "e4_unified.schema.json"),
        (_FIXTURES / "e2" / "minimal-baseline-1.5_consolidated.json", "baseline_patrimonial.schema.json"),
    ],
)
def test_pipeline_golden_fixture_matches_schema(fixture_path: Path, schema_name: str):
    jsonschema = pytest.importorskip("jsonschema")

    data = json.loads(fixture_path.read_text(encoding="utf-8"))
    schema = json.loads((_SCHEMAS / schema_name).read_text(encoding="utf-8"))
    jsonschema.validate(data, schema)
