"""Emite tipos TypeScript do dialeto JSON Schema usado pelo artefato E5."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dev.report_analysis_schema_refinement import RefinementError, parse_discriminant_all_of

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = REPO_ROOT / "config" / "schemas" / "e5_analysis.schema.json"
GENERATED_PATH = REPO_ROOT / "frontend" / "src" / "generated" / "report-analysis.ts"

_SUPPORTED_KEYS = {
    "$defs",
    "$ref",
    "$schema",
    "additionalProperties",
    "allOf",
    "const",
    "description",
    "enum",
    "exclusiveMinimum",
    "else",
    "format",
    # `if`/`then`/`else` restringem *quais instâncias* são válidas, não *quais
    # campos existem* — o tipo TS emitido é a união de todas as formas válidas,
    # que é exatamente a forma incondicional. Validação-only: o renderer os
    # ignora de propósito (A40.l63 · ADR-390 D1).
    "if",
    "items",
    "maxItems",
    "maximum",
    "minItems",
    "minLength",
    "minimum",
    "oneOf",
    "pattern",
    "patternProperties",
    "prefixItems",
    "then",
    "properties",
    "required",
    "title",
    "type",
    "uniqueItems",
    "x-codegen",
}
_PRIMITIVES = {
    "boolean": "boolean",
    "integer": "number",
    "null": "null",
    "number": "number",
    "string": "string",
}
_PATTERN_KEY_TYPES = {
    "^[0-9]+$": "`${number}`",
    "^[A-Z][A-Z0-9_]*$": "Uppercase<string>",
    "^[a-z_]+$": "Lowercase<string>",
    "^s([1-9]|10)$": '"s1" | "s2" | "s3" | "s4" | "s5" | "s6" | "s7" | "s8" | "s9" | "s10"',
    "^idade_[a-z_][a-z0-9_]*_if$": "`idade_${string}_if`",
}


class SchemaCodegenError(ValueError):
    """Schema usa construção que o emitter deliberadamente não interpreta."""


@dataclass(frozen=True)
class SchemaDocument:
    path: Path
    root_name: str
    definition_prefix: str
    schema: dict[str, Any]


def _pascal(value: str) -> str:
    return "".join(part.capitalize() for part in re.split(r"[^A-Za-z0-9]+", value) if part)


def _load_document(path: Path, *, root_name: str, prefix: str) -> SchemaDocument:
    schema = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(schema, dict):
        raise SchemaCodegenError(f"{path}: expected object schema, got {type(schema).__name__}")
    return SchemaDocument(path, root_name, prefix, schema)


def _external_ref_filenames(schema: dict[str, Any]) -> set[str]:
    refs: set[str] = set()
    pending: list[Any] = [schema]
    while pending:
        ref, children = _external_ref_and_children(pending.pop())
        if ref:
            refs.add(ref)
        pending.extend(children)
    return refs


def _external_ref_and_children(value: Any) -> tuple[str | None, list[Any]]:
    if isinstance(value, list):
        return None, value
    if not isinstance(value, dict):
        return None, []
    ref = value.get("$ref")
    filename = ref.split("#", maxsplit=1)[0] if isinstance(ref, str) else None
    return (filename if filename and not filename.startswith("#") else None), list(value.values())


class TypeScriptSchemaEmitter:
    """Renderer determinístico e fail-closed para o contrato E5 medido."""

    def __init__(self, schema_path: Path = SCHEMA_PATH) -> None:
        self.main = _load_document(schema_path, root_name="E5AnalysisArtifact", prefix="")
        self.documents = [self.main, *self._load_external_documents()]
        for document in self.documents:
            self._validate_schema(document.schema, document, "$")

    def _load_external_documents(self) -> list[SchemaDocument]:
        return [
            self._load_external_document(ref)
            for ref in sorted(_external_ref_filenames(self.main.schema))
        ]

    def _load_external_document(self, ref: str) -> SchemaDocument:
        if Path(ref).name != ref:
            raise SchemaCodegenError(
                f"external $ref must be a sibling schema filename, got {ref!r}"
            )
        path = self.main.path.parent / ref
        if not path.is_file():
            raise SchemaCodegenError(f"external $ref does not exist: {path}")
        base = _pascal(path.name.removesuffix(".schema.json"))
        return _load_document(path, root_name=f"{base}Artifact", prefix=base)

    def _validate_schema(
        self, schema: dict[str, Any], document: SchemaDocument, pointer: str
    ) -> None:
        unknown = sorted(set(schema) - _SUPPORTED_KEYS)
        if unknown:
            raise SchemaCodegenError(
                f"{document.path}:{pointer}: unsupported structural keyword(s): {', '.join(unknown)}"
            )
        for container in ("$defs", "properties", "patternProperties"):
            self._validate_mapping_children(schema, container, document, pointer)
        self._validate_additional_properties(schema, document, pointer)
        self._validate_items(schema, document, pointer)
        self._validate_sequence_children(schema, "allOf", document, pointer)
        self._validate_sequence_children(schema, "prefixItems", document, pointer)
        self._validate_sequence_children(schema, "oneOf", document, pointer)

    def _validate_mapping_children(
        self, schema: dict[str, Any], key: str, document: SchemaDocument, pointer: str
    ) -> None:
        for name, child in (schema.get(key) or {}).items():
            self._validate_child(child, document, f"{pointer}/{key}/{name}")

    def _validate_additional_properties(
        self, schema: dict[str, Any], document: SchemaDocument, pointer: str
    ) -> None:
        additional = schema.get("additionalProperties")
        if isinstance(additional, dict):
            self._validate_child(additional, document, f"{pointer}/additionalProperties")

    def _validate_items(
        self, schema: dict[str, Any], document: SchemaDocument, pointer: str
    ) -> None:
        items = schema.get("items")
        if isinstance(items, dict):
            self._validate_child(items, document, f"{pointer}/items")
        elif isinstance(items, list) or (items is not None and not isinstance(items, bool)):
            raise SchemaCodegenError(f"{document.path}:{pointer}/items: tuple schemas unsupported")

    def _validate_sequence_children(
        self, schema: dict[str, Any], key: str, document: SchemaDocument, pointer: str
    ) -> None:
        for index, child in enumerate(schema.get(key) or []):
            self._validate_child(child, document, f"{pointer}/{key}/{index}")

    def _validate_child(self, child: Any, document: SchemaDocument, pointer: str) -> None:
        if not isinstance(child, dict):
            raise SchemaCodegenError(
                f"{document.path}:{pointer}: expected schema object, got {type(child).__name__}"
            )
        self._validate_schema(child, document, pointer)

    def render(self) -> str:
        sections = [
            "// Code generated by dev/codegen_report_analysis.py; DO NOT EDIT.",
            "// Source: config/schemas/e5_analysis.schema.json",
            "",
        ]
        for document in self.documents:
            sections.extend(self._render_definitions(document))
        for document in self.documents[1:]:
            sections.extend(self._render_named(document.root_name, document.schema, document))
        sections.extend(self._render_named(self.main.root_name, self.main.schema, self.main))
        return "\n".join(sections).rstrip() + "\n"

    def _render_definitions(self, document: SchemaDocument) -> list[str]:
        rendered: list[str] = []
        for name, schema in (document.schema.get("$defs") or {}).items():
            type_name = f"{document.definition_prefix}{name}"
            rendered.extend(self._render_named(type_name, schema, document))
        return rendered

    def _render_named(
        self, name: str, schema: dict[str, Any], document: SchemaDocument
    ) -> list[str]:
        rendered = self._render_type(schema, document, "$", 0)
        return [f"export type {name} = {rendered};", ""]

    def _render_type(
        self,
        schema: dict[str, Any],
        document: SchemaDocument,
        pointer: str,
        level: int,
    ) -> str:
        if "allOf" in schema:
            return self._render_all_of(schema, document, pointer, level)
        if "$ref" in schema:
            return self._render_ref(str(schema["$ref"]), document, pointer)
        if "const" in schema:
            raise SchemaCodegenError(
                f"{document.path}:{pointer}: const only supported as allOf discriminant"
            )
        return self._render_declared_type(schema, document, pointer, level)

    def _render_declared_type(
        self,
        schema: dict[str, Any],
        document: SchemaDocument,
        pointer: str,
        level: int,
    ) -> str:
        if "enum" in schema:
            return " | ".join(json.dumps(item, ensure_ascii=False) for item in schema["enum"])
        if "oneOf" in schema:
            return self._render_one_of(schema["oneOf"], document, pointer, level)
        declared_type = schema.get("type")
        if isinstance(declared_type, list):
            return self._render_type_union(declared_type, schema, document, pointer, level)
        if isinstance(declared_type, str):
            return self._render_simple_type(declared_type, schema, document, pointer, level)
        return self._render_inferred_object(schema, document, pointer, level)

    def _render_all_of(
        self, schema: dict[str, Any], document: SchemaDocument, pointer: str, level: int
    ) -> str:
        try:
            refinement = parse_discriminant_all_of(schema, document.schema.get("$defs") or {})
        except RefinementError as exc:
            raise SchemaCodegenError(f"{document.path}:{pointer}: {exc}") from exc
        base_type = self._render_ref(refinement.ref, document, f"{pointer}/allOf/0")
        discriminant = self._render_discriminant(refinement.property_name, refinement.value, level)
        return f"{base_type} & {discriminant}"

    @staticmethod
    def _render_discriminant(name: str, value: Any, level: int) -> str:
        indent = "  " * level
        quoted_name = json.dumps(name, ensure_ascii=False)
        literal = json.dumps(value, ensure_ascii=False)
        return f"{{\n{indent}  {quoted_name}: {literal};\n{indent}}}"

    def _render_inferred_object(
        self, schema: dict[str, Any], document: SchemaDocument, pointer: str, level: int
    ) -> str:
        if schema.get("properties") or schema.get("patternProperties"):
            return self._render_object(schema, document, pointer, level)
        raise SchemaCodegenError(f"{document.path}:{pointer}: schema has no renderable type")

    def _render_one_of(
        self, variants: list[dict[str, Any]], document: SchemaDocument, pointer: str, level: int
    ) -> str:
        rendered = [
            self._render_type(item, document, f"{pointer}/oneOf/{index}", level)
            for index, item in enumerate(variants)
        ]
        return " | ".join(dict.fromkeys(rendered))

    def _render_type_union(
        self,
        variants: list[str],
        schema: dict[str, Any],
        document: SchemaDocument,
        pointer: str,
        level: int,
    ) -> str:
        rendered = [
            self._render_simple_type(item, schema, document, pointer, level) for item in variants
        ]
        return " | ".join(dict.fromkeys(rendered))

    def _render_simple_type(
        self,
        declared_type: str,
        schema: dict[str, Any],
        document: SchemaDocument,
        pointer: str,
        level: int,
    ) -> str:
        if declared_type in _PRIMITIVES:
            return _PRIMITIVES[declared_type]
        if declared_type == "array":
            return self._render_array(schema, document, pointer, level)
        if declared_type == "object":
            return self._render_object(schema, document, pointer, level)
        raise SchemaCodegenError(f"{document.path}:{pointer}: unsupported type {declared_type!r}")

    def _render_array(
        self, schema: dict[str, Any], document: SchemaDocument, pointer: str, level: int
    ) -> str:
        prefix_items = schema.get("prefixItems")
        if prefix_items:
            return self._render_tuple(schema, document, pointer, level)
        items = schema.get("items")
        if not isinstance(items, dict):
            raise SchemaCodegenError(f"{document.path}:{pointer}: array requires object `items`")
        item_type = self._render_type(items, document, f"{pointer}/items", level)
        return f"Array<{item_type}>"

    def _render_tuple(
        self, schema: dict[str, Any], document: SchemaDocument, pointer: str, level: int
    ) -> str:
        prefix_items = schema["prefixItems"]
        length = len(prefix_items)
        exact = schema.get("items") is False and schema.get("minItems") == length
        if not exact or schema.get("maxItems") != length:
            raise SchemaCodegenError(f"{document.path}:{pointer}: tuple must fix its exact length")
        members = [
            self._render_type(item, document, f"{pointer}/prefixItems/{index}", level)
            for index, item in enumerate(prefix_items)
        ]
        return f"[{', '.join(members)}]"

    def _render_object(
        self,
        schema: dict[str, Any],
        document: SchemaDocument,
        pointer: str,
        level: int,
    ) -> str:
        properties = schema.get("properties") or {}
        patterns = schema.get("patternProperties") or {}
        if not properties:
            return self._render_map_object(schema, patterns, document, pointer, level)
        fixed = self._render_fixed_properties(schema, properties, document, pointer, level)
        pattern_maps = self._render_pattern_maps(patterns, document, pointer, level)
        return " & ".join([fixed, *pattern_maps])

    def _render_map_object(
        self,
        schema: dict[str, Any],
        patterns: dict[str, dict[str, Any]],
        document: SchemaDocument,
        pointer: str,
        level: int,
    ) -> str:
        if patterns:
            values = self._pattern_value_union(patterns, document, pointer, level)
            return f"Record<string, {values}>"
        additional = schema.get("additionalProperties")
        if isinstance(additional, dict):
            return self._render_additional_map(additional, document, pointer, level)
        if self._is_opaque(schema):
            return "Record<string, never>"
        raise SchemaCodegenError(
            f"{document.path}:{pointer}: shape-less object requires typed map or x-codegen.opaque"
        )

    def _render_additional_map(
        self,
        additional: dict[str, Any],
        document: SchemaDocument,
        pointer: str,
        level: int,
    ) -> str:
        value = self._render_type(additional, document, f"{pointer}/additionalProperties", level)
        return f"Record<string, {value}>"

    def _render_fixed_properties(
        self,
        schema: dict[str, Any],
        properties: dict[str, dict[str, Any]],
        document: SchemaDocument,
        pointer: str,
        level: int,
    ) -> str:
        required = set(schema.get("required") or [])
        indent = "  " * level
        lines = ["{"]
        for name, child in properties.items():
            optional = "" if name in required else "?"
            child_type = self._render_type(
                child, document, f"{pointer}/properties/{name}", level + 1
            )
            lines.append(self._property_line(indent, name, optional, child_type))
        lines.append(f"{indent}}}")
        return "\n".join(lines)

    @staticmethod
    def _property_line(indent: str, name: str, optional: str, child_type: str) -> str:
        quoted = json.dumps(name, ensure_ascii=False)
        return f"{indent}  {quoted}{optional}: {child_type};"

    def _render_pattern_maps(
        self,
        patterns: dict[str, dict[str, Any]],
        document: SchemaDocument,
        pointer: str,
        level: int,
    ) -> list[str]:
        rendered: list[str] = []
        for pattern, child in patterns.items():
            key_type = _PATTERN_KEY_TYPES.get(pattern)
            if key_type is None:
                raise SchemaCodegenError(
                    f"{document.path}:{pointer}/patternProperties/{pattern}: unsupported key pattern"
                )
            value = self._render_type(
                child, document, f"{pointer}/patternProperties/{pattern}", level
            )
            rendered.append(f"Partial<Record<{key_type}, {value}>>")
        return rendered

    def _pattern_value_union(
        self,
        patterns: dict[str, dict[str, Any]],
        document: SchemaDocument,
        pointer: str,
        level: int,
    ) -> str:
        values = [
            self._render_type(child, document, f"{pointer}/patternProperties/{pattern}", level)
            for pattern, child in patterns.items()
        ]
        return " | ".join(dict.fromkeys(values))

    def _render_ref(self, ref: str, document: SchemaDocument, pointer: str) -> str:
        if ref.startswith("#/$defs/"):
            name = ref.removeprefix("#/$defs/")
            if name not in (document.schema.get("$defs") or {}):
                raise SchemaCodegenError(
                    f"{document.path}:{pointer}: unresolved local $ref {ref!r}"
                )
            return f"{document.definition_prefix}{name}"
        filename, separator, fragment = ref.partition("#")
        target = next((item for item in self.documents if item.path.name == filename), None)
        if target is None or (separator and fragment):
            raise SchemaCodegenError(
                f"{document.path}:{pointer}: unsupported external $ref {ref!r}"
            )
        return target.root_name

    @staticmethod
    def _is_opaque(schema: dict[str, Any]) -> bool:
        metadata = schema.get("x-codegen")
        return isinstance(metadata, dict) and metadata.get("opaque") is True


def render_typescript(schema_path: Path = SCHEMA_PATH) -> str:
    return TypeScriptSchemaEmitter(schema_path).render()
