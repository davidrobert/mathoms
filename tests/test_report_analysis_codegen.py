from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from dev.report_analysis_codegen import SchemaCodegenError, render_typescript


def _write_schema(tmp_path: Path, schema: dict) -> Path:
    path = tmp_path / "e5_analysis.schema.json"
    path.write_text(json.dumps(schema), encoding="utf-8")
    return path


def _root(properties: dict, *, additional_properties: bool = True) -> dict:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "fixture",
        "type": "object",
        "required": [],
        "properties": properties,
        "additionalProperties": additional_properties,
    }


def _schema_with_typed_labels() -> dict:
    return _root(
        {
            "labels": {
                "type": "object",
                "patternProperties": {"^[A-Z][A-Z0-9_]*$": {"type": "string"}},
                "additionalProperties": False,
            },
            "known": {"type": "number"},
        }
    )


def test_codegen_is_deterministic_and_top_level_open_does_not_leak_index_signature(
    tmp_path: Path,
) -> None:
    path = _write_schema(tmp_path, _schema_with_typed_labels())

    first = render_typescript(path)
    second = render_typescript(path)

    assert first == second
    assert "Record<string, string>" in first
    assert "[key: string]" not in first
    assert '"known"?: number' in first


def test_codegen_opaque_object_is_never_map(tmp_path: Path) -> None:
    path = _write_schema(
        tmp_path,
        _root(
            {
                "empty": {
                    "type": "object",
                    "x-codegen": {"opaque": True, "reason": "produtor vazio", "owner": "T1"},
                }
            }
        ),
    )

    assert '"empty"?: Record<string, never>' in render_typescript(path)


def test_codegen_resolves_known_external_root(tmp_path: Path) -> None:
    external = _root({"required_value": {"type": "string"}})
    (tmp_path / "other.schema.json").write_text(json.dumps(external), encoding="utf-8")
    path = _write_schema(tmp_path, _root({"other": {"$ref": "other.schema.json"}}))

    rendered = render_typescript(path)

    assert "export type OtherArtifact" in rendered
    assert '"other"?: OtherArtifact' in rendered


@pytest.mark.parametrize(
    ("fragment", "expected"),
    [
        ({"allOf": [{"type": "string"}]}, "unsupported structural keyword(s): allOf"),
        ({"type": "array"}, "array requires object `items`"),
        ({"type": "object"}, "shape-less object requires"),
    ],
)
def test_codegen_fails_closed_with_pointer(tmp_path: Path, fragment: dict, expected: str) -> None:
    path = _write_schema(tmp_path, _root({"broken": fragment}))

    with pytest.raises(SchemaCodegenError, match=re.escape(expected)):
        render_typescript(path)


def test_schema_field_mutation_changes_generated_type(tmp_path: Path) -> None:
    path = _write_schema(tmp_path, _root({"field": {"type": "string"}}))
    before = render_typescript(path)
    path = _write_schema(tmp_path, _root({"field": {"type": "number"}}))

    assert render_typescript(path) != before


def test_fixed_array_prefix_items_generate_tuple(tmp_path: Path) -> None:
    point = {
        "type": "array",
        "prefixItems": [{"type": "integer"}, {"type": "number"}],
        "items": False,
        "minItems": 2,
        "maxItems": 2,
    }
    path = _write_schema(tmp_path, _root({"path": {"type": "array", "items": point}}))

    rendered = render_typescript(path)

    assert "Array<[number, number]>" in rendered
