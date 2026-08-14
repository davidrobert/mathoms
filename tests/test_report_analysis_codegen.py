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


def _window_definition(*, required: bool = True) -> dict:
    return {
        "type": "object",
        "required": ["name"] if required else [],
        "additionalProperties": False,
        "properties": {"name": {"enum": ["3m", "6m"]}},
    }


def _all_of_window_schema(
    *, overlay_name: str = "name", const: str = "3m", required: bool = True
) -> dict:
    schema = _root(
        {
            "window": {
                "allOf": [
                    {"$ref": "#/$defs/Window"},
                    {"properties": {overlay_name: {"const": const}}},
                ]
            }
        }
    )
    schema["$defs"] = {"Window": _window_definition(required=required)}
    return schema


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
        ({"allOf": [{"type": "string"}]}, "allOf requires ref + const overlay"),
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


def test_all_of_narrows_existing_property_with_const(tmp_path: Path) -> None:
    rendered = render_typescript(_write_schema(tmp_path, _all_of_window_schema()))

    assert '"window"?: Window & {' in rendered
    assert '"name": "3m"' in rendered


def test_all_of_rejects_overlay_that_adds_property(tmp_path: Path) -> None:
    with pytest.raises(SchemaCodegenError, match="must narrow required property"):
        path = _write_schema(tmp_path, _all_of_window_schema(overlay_name="unknown"))
        render_typescript(path)


def test_all_of_rejects_optional_or_incompatible_discriminant(tmp_path: Path) -> None:
    with pytest.raises(SchemaCodegenError, match="must narrow required property"):
        optional = _all_of_window_schema(required=False)
        render_typescript(_write_schema(tmp_path, optional))

    with pytest.raises(SchemaCodegenError, match="incompatible const"):
        incompatible = _all_of_window_schema(const="12m")
        render_typescript(_write_schema(tmp_path, incompatible))


def test_real_schema_renders_closed_window_discriminants() -> None:
    rendered = render_typescript()

    for period in ("3m", "6m", "12m", "ytd"):
        assert f'"{period}": FluxoJanelaInterativa & {{' in rendered
        assert f'"janela": "{period}";' in rendered
