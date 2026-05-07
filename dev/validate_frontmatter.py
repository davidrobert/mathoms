#!/usr/bin/env python3
"""Valida frontmatter YAML de notas em docs/ contra schemas em docs/_schemas/ (ADR-182, F1.C)."""
# Carrega schema via mapping type: → note-<type>.schema.json. Aceita paths
# (pre-commit) ou varre docs/ (CI). Sem frontmatter / type não-mapeado / YAML
# inválido → silent skip default; --strict eleva todos a erro. Schema ausente
# → erro hard.

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import jsonschema
import yaml

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
SCHEMAS = DOCS / "_schemas"

# Mapping type → schema filename. Adicione entrada nova ao introduzir tipo.
SCHEMA_BY_TYPE: dict[str, str] = {
    "adr": "note-adr.schema.json",
    "lane": "note-lane.schema.json",
    "plan": "note-plan.schema.json",
    "changelog-entry": "note-changelog-entry.schema.json",
    "track": "note-track.schema.json",
    "domain-rule": "note-domain-rule.schema.json",
}

# Subdiretórios excluídos do walk default (consumo interno ou legado).
EXCLUDED_DIRS = {"_MOC", "_schemas", "archive", "agent_prompts"}


@dataclass(frozen=True)
class ValidationError:
    """Erro de validação numa nota — path, campo, motivo."""

    path: Path
    field: str
    message: str


def load_schemas() -> dict[str, dict]:
    """Carrega cada schema declarado em SCHEMA_BY_TYPE; falha se ausente."""
    loaded: dict[str, dict] = {}
    for note_type, filename in SCHEMA_BY_TYPE.items():
        schema_path = SCHEMAS / filename
        if not schema_path.is_file():
            raise FileNotFoundError(
                f"schema {filename!r} não encontrado em {SCHEMAS.relative_to(ROOT)}/. "
                f"Rode F1.A primeiro."
            )
        loaded[note_type] = json.loads(schema_path.read_text(encoding="utf-8"))
    return loaded


def _coerce_dates_to_iso(value):
    """Converte datetime.date/datetime → ISO string recursivamente. Schemas usam format: date."""
    import datetime as _dt

    if isinstance(value, _dt.datetime):
        return value.date().isoformat()
    if isinstance(value, _dt.date):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: _coerce_dates_to_iso(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_coerce_dates_to_iso(v) for v in value]
    return value


def parse_frontmatter(md_path: Path) -> dict | None:
    """Extrai YAML entre `---` ... `---`. None se ausente; ValueError se inválido."""
    content = md_path.read_text(encoding="utf-8")
    if not content.startswith("---"):
        return None
    end_marker = content.find("\n---", 3)
    if end_marker == -1:
        raise ValueError("frontmatter aberto com '---' mas nunca fechado")
    yaml_block = content[3:end_marker].lstrip("\n")
    try:
        data = yaml.safe_load(yaml_block)
    except yaml.YAMLError as exc:
        raise ValueError(f"YAML inválido: {exc}") from exc
    if data is None:
        return None
    if not isinstance(data, dict):
        raise ValueError(
            f"frontmatter deve ser mapping YAML, recebido: {type(data).__name__}={data!r}"
        )
    return _coerce_dates_to_iso(data)


def _format_path(path_parts: Iterable[str | int]) -> str:
    parts = [str(p) for p in path_parts]
    return ".".join(parts) if parts else "<root>"


def _err_offender(value: object) -> str:
    """Renderiza valor ofensor curto, com tipo, evitando dump enorme."""
    repr_value = repr(value)
    if len(repr_value) > 120:
        repr_value = repr_value[:117] + "..."
    return f"{type(value).__name__}={repr_value}"


def _from_jsonschema_error(md_path: Path, exc: jsonschema.ValidationError) -> ValidationError:
    field = _format_path(exc.absolute_path)
    schema = exc.schema or {}
    expected_parts: list[str] = []
    if "enum" in schema:
        expected_parts.append(f"enum {schema['enum']}")
    if "pattern" in schema:
        expected_parts.append(f"pattern {schema['pattern']!r}")
    if "type" in schema:
        expected_parts.append(f"type {schema['type']!r}")
    if "required" in schema and exc.validator == "required":
        expected_parts.append(f"campos obrigatórios {schema['required']}")
    expected = " | ".join(expected_parts) if expected_parts else exc.message
    received = _err_offender(exc.instance)
    message = f"esperado: {expected}\n  recebido: {received}"
    return ValidationError(path=md_path, field=field, message=message)


def validate_note(
    md_path: Path, schemas: dict[str, dict], *, strict: bool
) -> list[ValidationError]:
    """Valida 1 nota; retorna lista de erros (vazia ⇒ ok)."""
    try:
        fm = parse_frontmatter(md_path)
    except ValueError as exc:
        return [ValidationError(path=md_path, field="<frontmatter>", message=str(exc))]
    if fm is None:
        return _strict_skip(md_path, "<frontmatter>", "ausente", strict=strict)
    note_type = fm.get("type")
    if note_type is None:
        return _strict_skip(md_path, "type", "campo ausente no frontmatter", strict=strict)
    if note_type not in schemas:
        msg = f"type {note_type!r} não mapeado em SCHEMA_BY_TYPE {sorted(schemas)}"
        return _strict_skip(md_path, "type", msg, strict=strict)
    return _validate_against_schema(md_path, fm, schemas[note_type])


def _strict_skip(md_path: Path, field: str, message: str, *, strict: bool) -> list[ValidationError]:
    if strict:
        return [ValidationError(path=md_path, field=field, message=message)]
    return []


def _validate_against_schema(md_path: Path, fm: dict, schema: dict) -> list[ValidationError]:
    validator = jsonschema.Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(fm), key=lambda e: list(e.absolute_path))
    return [_from_jsonschema_error(md_path, e) for e in errors]


def collect_md_files(root: Path) -> list[Path]:
    """Walk de `root`, exclui subdirs em EXCLUDED_DIRS. Ordena para output estável."""
    files: list[Path] = []
    for path in root.rglob("*.md"):
        if any(part in EXCLUDED_DIRS for part in path.relative_to(root).parts):
            continue
        files.append(path)
    return sorted(files)


def format_error(err: ValidationError) -> str:
    """Renderiza erro humano-legível com path relativo + campo + mensagem."""
    rel = _relpath_to_root(err.path)
    return f"✗ {rel}\n  campo: {err.field}\n  {err.message}"


def _relpath_to_root(path: Path) -> Path:
    """Converte para path relativo a ROOT; fallback no path absoluto se fora."""
    if not path.is_absolute():
        return path
    try:
        return path.relative_to(ROOT)
    except ValueError:
        return path


def _resolve_targets(arg_paths: list[str]) -> list[Path]:
    if not arg_paths:
        return collect_md_files(DOCS)
    resolved: list[Path] = []
    for raw in arg_paths:
        path = Path(raw).resolve()
        if path.suffix == ".md" and path.is_file():
            resolved.append(path)
    return resolved


def _summarize_types(notes_by_type: dict[str, int]) -> str:
    if not notes_by_type:
        return ""
    parts = [f"{n} {t}" for t, n in sorted(notes_by_type.items())]
    return " (" + ", ".join(parts) + ")"


def main() -> int:
    args = _parse_args()
    try:
        schemas = load_schemas()
    except FileNotFoundError as exc:
        print(f"erro: {exc}", file=sys.stderr)
        return 1
    targets = _resolve_targets(args.paths)
    errors, validated, by_type = _run_validation(targets, schemas, strict=args.strict)
    return _report(errors, validated, by_type)


def _run_validation(
    targets: list[Path], schemas: dict[str, dict], *, strict: bool
) -> tuple[list[ValidationError], int, dict[str, int]]:
    errors: list[ValidationError] = []
    validated = 0
    by_type: dict[str, int] = {}
    for md_path in targets:
        note_errors = validate_note(md_path, schemas, strict=strict)
        if note_errors:
            errors.extend(note_errors)
        try:
            fm = parse_frontmatter(md_path)
        except ValueError:
            fm = None
        if fm and fm.get("type") in schemas:
            validated += 1
            by_type[fm["type"]] = by_type.get(fm["type"], 0) + 1
    return errors, validated, by_type


def _report(errors: list[ValidationError], validated: int, by_type: dict[str, int]) -> int:
    if errors:
        for err in errors:
            print(format_error(err))
            print()
        notes_with_err = len({e.path for e in errors})
        print(f"{len(errors)} erro(s) em {notes_with_err} nota(s) (de {validated} validadas).")
        return 1
    suffix = _summarize_types(by_type)
    plural = "s" if validated != 1 else ""
    print(f"✓ {validated} nota{plural} validada{plural}{suffix}.")
    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument(
        "paths",
        nargs="*",
        help="paths específicos (pre-commit mode); default: walk docs/",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="falha se nota tem frontmatter mas type ausente/não mapeado",
    )
    return parser.parse_args()


if __name__ == "__main__":
    sys.exit(main())
