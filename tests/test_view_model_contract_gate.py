from __future__ import annotations

from pathlib import Path

import pytest

from dev.check_view_model_contract import (
    check_opaque_baseline,
    find_missing_literal_schemas,
    find_opaque_readers,
    inspect_opaque_blocks,
)


def _schema(block: dict) -> dict:
    return {"type": "object", "properties": {"programa_milhas": block}}


def _opaque(**overrides: object) -> dict:
    metadata = {"opaque": True, "reason": "produtor emite vazio", "owner": "A40.l5"}
    metadata.update(overrides)
    return {"type": "object", "x-codegen": metadata}


def test_valid_opaque_block_is_inventory() -> None:
    opaque, violations = inspect_opaque_blocks(_schema(_opaque()))

    assert opaque == {"programa_milhas"}
    assert violations == []


@pytest.mark.parametrize(
    "block",
    [
        {"type": "object"},
        {"type": "object", "x-codegen": {"opaque": True}},
        _opaque(reason=""),
        {**_opaque(), "properties": {"valor": {"type": "number"}}},
    ],
)
def test_invalid_opaque_metadata_fails(block: dict) -> None:
    _, violations = inspect_opaque_blocks(_schema(block))

    assert violations


def test_opaque_ratchet_rejects_increase_and_requires_freezing_decrease(tmp_path: Path) -> None:
    baseline = tmp_path / "baseline.txt"
    baseline.write_text("programa_milhas\n", encoding="utf-8")

    assert check_opaque_baseline({"programa_milhas"}, baseline) == []
    assert check_opaque_baseline({"programa_milhas", "novo"}, baseline)
    assert check_opaque_baseline(set(), baseline)


@pytest.mark.parametrize(
    "source",
    [
        "const value = data.programa_milhas;",
        'const value = data["programa_milhas"];',
        "const { programa_milhas } = data;",
    ],
)
def test_opaque_reader_forms_fail(tmp_path: Path, source: str) -> None:
    (tmp_path / "reader.ts").write_text(source, encoding="utf-8")

    violations = find_opaque_readers({"programa_milhas"}, tmp_path)

    assert len(violations) == 1
    assert violations[0].code == "OPAQUE_READER"


def test_generated_file_is_excluded_from_reader_scan(tmp_path: Path) -> None:
    generated = tmp_path / "generated"
    generated.mkdir()
    (generated / "report-analysis.ts").write_text(
        "type T = { programa_milhas: never };", encoding="utf-8"
    )

    assert find_opaque_readers({"programa_milhas"}, tmp_path) == []


def test_literal_validate_dict_schema_must_exist(tmp_path: Path) -> None:
    source = tmp_path / "source"
    schemas = tmp_path / "schemas"
    source.mkdir()
    schemas.mkdir()
    (source / "calls.py").write_text(
        'validate_dict({}, "missing.schema.json")\nvalidate_dict({}, schema_name)\n',
        encoding="utf-8",
    )

    violations = find_missing_literal_schemas([source], schemas)

    assert len(violations) == 1
    assert "missing.schema.json" in violations[0].detail
