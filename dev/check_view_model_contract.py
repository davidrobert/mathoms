#!/usr/bin/env python3
"""Gate E5→frontend: codegen em sync, opacidade governada e schemas resolvíveis."""

from __future__ import annotations

import ast
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT_BOOTSTRAP = Path(__file__).resolve().parent.parent
if str(REPO_ROOT_BOOTSTRAP) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT_BOOTSTRAP))

from dev.report_analysis_codegen import GENERATED_PATH, REPO_ROOT, SCHEMA_PATH, render_typescript

OPAQUE_BASELINE = REPO_ROOT / "dev" / "snapshots" / "e5_opaque_blocks.txt"
SCHEMA_DIR = REPO_ROOT / "config" / "schemas"
PYTHON_SCAN_ROOTS = ("backend", "dev", "pipeline", "scripts", "tests")
TYPESCRIPT_SCAN_ROOT = REPO_ROOT / "frontend" / "src"


@dataclass(frozen=True)
class ContractViolation:
    code: str
    detail: str

    def format(self) -> str:
        return f"[{self.code}] {self.detail}"


def load_schema(path: Path = SCHEMA_PATH) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _shape_less_object(block: dict[str, Any]) -> bool:
    return not (
        block.get("properties")
        or block.get("patternProperties")
        or isinstance(block.get("additionalProperties"), dict)
    )


def _opaque_metadata_violation(
    name: str, metadata: object, *, shape_less: bool
) -> ContractViolation | None:
    if metadata is None:
        detail = f"{name}: objeto sem shape exige x-codegen.opaque"
        return ContractViolation("OPAQUE", detail) if shape_less else None
    if not isinstance(metadata, dict):
        return ContractViolation("OPAQUE", f"{name}: x-codegen deve ser objeto")
    if set(metadata) != {"opaque", "reason", "owner"}:
        detail = f"{name}: x-codegen exige exatamente opaque, reason e owner"
        return ContractViolation("OPAQUE", detail)
    if metadata.get("opaque") is not True:
        return ContractViolation("OPAQUE", f"{name}: opaque deve ser true")
    if not _opaque_strings_valid(metadata):
        detail = f"{name}: reason e owner devem ser strings não vazias"
        return ContractViolation("OPAQUE", detail)
    if not shape_less:
        return ContractViolation("OPAQUE", f"{name}: bloco tipado não pode carregar opaque")
    return None


def _opaque_strings_valid(metadata: dict[str, Any]) -> bool:
    return all(
        isinstance(metadata.get(key), str) and metadata[key].strip() for key in ("reason", "owner")
    )


def inspect_opaque_blocks(schema: dict[str, Any]) -> tuple[set[str], list[ContractViolation]]:
    opaque: set[str] = set()
    violations: list[ContractViolation] = []
    for name, block in (schema.get("properties") or {}).items():
        if not isinstance(block, dict) or block.get("type") != "object":
            continue
        metadata = block.get("x-codegen")
        shape_less = _shape_less_object(block)
        violation = _opaque_metadata_violation(name, metadata, shape_less=shape_less)
        if violation:
            violations.append(violation)
            continue
        if metadata is not None:
            opaque.add(name)
    return opaque, violations


def check_opaque_baseline(
    actual: set[str], path: Path = OPAQUE_BASELINE
) -> list[ContractViolation]:
    expected = {
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    }
    if actual == expected:
        return []
    added = sorted(actual - expected)
    removed = sorted(expected - actual)
    detail = f"baseline={sorted(expected)!r}, atual={sorted(actual)!r}"
    if added:
        detail += f"; opacidade nova proibida={added!r}"
    if removed:
        detail += f"; melhoria exige baixar baseline={removed!r}"
    return [ContractViolation("OPAQUE_RATCHET", detail)]


def _reader_patterns(field: str) -> tuple[re.Pattern[str], ...]:
    escaped = re.escape(field)
    return (
        re.compile(rf"(?:\?\.|\.){escaped}\b"),
        re.compile(rf"\[\s*['\"]{escaped}['\"]\s*\]"),
        re.compile(rf"\{{[^}}]*\b{escaped}\b[^}}]*\}}\s*=", re.DOTALL),
    )


def find_opaque_readers(
    opaque: set[str], root: Path = TYPESCRIPT_SCAN_ROOT
) -> list[ContractViolation]:
    violations: list[ContractViolation] = []
    for path in sorted((*root.rglob("*.ts"), *root.rglob("*.tsx"))):
        if "generated" in path.parts:
            continue
        violations.extend(_opaque_readers_in_file(path, opaque))
    return violations


def _opaque_readers_in_file(path: Path, opaque: set[str]) -> list[ContractViolation]:
    text = path.read_text(encoding="utf-8")
    violations: list[ContractViolation] = []
    for field in sorted(opaque):
        match = next((p.search(text) for p in _reader_patterns(field) if p.search(text)), None)
        if match is None:
            continue
        line = text.count("\n", 0, match.start()) + 1
        display = path.relative_to(REPO_ROOT) if path.is_relative_to(REPO_ROOT) else path
        violations.append(ContractViolation("OPAQUE_READER", f"{display}:{line}: {field}"))
    return violations


def _validate_dict_schema_name(call: ast.Call) -> str | None:
    function_name = (
        call.func.attr if isinstance(call.func, ast.Attribute) else getattr(call.func, "id", "")
    )
    if function_name != "validate_dict":
        return None
    candidate: ast.expr | None = call.args[1] if len(call.args) > 1 else None
    for keyword in call.keywords:
        if keyword.arg == "schema_name":
            candidate = keyword.value
    return (
        candidate.value
        if isinstance(candidate, ast.Constant) and isinstance(candidate.value, str)
        else None
    )


def find_missing_literal_schemas(
    roots: Iterable[Path], schema_dir: Path = SCHEMA_DIR
) -> list[ContractViolation]:
    violations: list[ContractViolation] = []
    for root in roots:
        for path in sorted(root.rglob("*.py")):
            violations.extend(_missing_schemas_in_file(path, schema_dir))
    return violations


def _missing_schemas_in_file(path: Path, schema_dir: Path) -> list[ContractViolation]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (SyntaxError, UnicodeDecodeError):
        return []
    violations: list[ContractViolation] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        schema_name = _validate_dict_schema_name(node)
        if schema_name and not (schema_dir / schema_name).is_file():
            violations.append(_missing_schema_violation(path, node.lineno, schema_name))
    return violations


def _missing_schema_violation(path: Path, line: int, schema_name: str) -> ContractViolation:
    relative = path.relative_to(REPO_ROOT) if path.is_relative_to(REPO_ROOT) else path
    detail = f"{relative}:{line}: validate_dict aponta para schema inexistente {schema_name!r}"
    return ContractViolation("SCHEMA_NAME", detail)


def check_generated_sync() -> list[ContractViolation]:
    rendered = render_typescript()
    if GENERATED_PATH.is_file() and GENERATED_PATH.read_text(encoding="utf-8") == rendered:
        return []
    return [
        ContractViolation(
            "CODEGEN_SYNC", "rode python3 dev/codegen_report_analysis.py e commite o resultado"
        )
    ]


def collect_violations() -> list[ContractViolation]:
    schema = load_schema()
    opaque, violations = inspect_opaque_blocks(schema)
    violations += check_opaque_baseline(opaque)
    violations += find_opaque_readers(opaque)
    roots = [REPO_ROOT / name for name in PYTHON_SCAN_ROOTS]
    violations += find_missing_literal_schemas(roots)
    violations += check_generated_sync()
    return violations


def main() -> int:
    violations = collect_violations()
    for violation in violations:
        print(violation.format(), file=sys.stderr)
    if violations:
        print(f"check_view_model_contract: {len(violations)} violação(ões)", file=sys.stderr)
        return 1
    print("check_view_model_contract: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
