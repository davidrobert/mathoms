"""Reconhece refinamentos discriminados seguros do schema E5."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

_ANNOTATIONS = {"description", "title"}


class RefinementError(ValueError):
    """O allOf não pertence ao subconjunto seguro do codegen."""


@dataclass(frozen=True)
class DiscriminantRefinement:
    ref: str
    property_name: str
    value: Any


def parse_discriminant_all_of(
    schema: dict[str, Any], definitions: dict[str, Any]
) -> DiscriminantRefinement:
    if set(schema) - {"allOf", *_ANNOTATIONS}:
        raise RefinementError("allOf has structural siblings")
    variants = schema.get("allOf")
    if not isinstance(variants, list) or len(variants) != 2:
        raise RefinementError("allOf requires ref + const overlay")
    ref, target = _parse_closed_base(variants[0], definitions)
    name, value = _parse_const_overlay(variants[1], target)
    return DiscriminantRefinement(ref, name, value)


def _parse_closed_base(base: object, definitions: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    ref = base.get("$ref") if isinstance(base, dict) and set(base) == {"$ref"} else None
    if not isinstance(ref, str) or not ref.startswith("#/$defs/"):
        raise RefinementError("allOf base must be local $ref")
    target = definitions.get(ref.removeprefix("#/$defs/"))
    if not isinstance(target, dict) or target.get("type") != "object":
        raise RefinementError("allOf base must resolve to object")
    closed = target.get("additionalProperties") is False
    if not closed or not isinstance(target.get("properties"), dict):
        raise RefinementError("allOf base must be closed object")
    return ref, target


def _parse_const_overlay(overlay: object, target: dict[str, Any]) -> tuple[str, Any]:
    properties = overlay.get("properties") if isinstance(overlay, dict) else None
    if not isinstance(overlay, dict) or set(overlay) != {"properties"}:
        properties = None
    if not isinstance(properties, dict) or len(properties) != 1:
        raise RefinementError("allOf overlay needs one property")
    name, constraint = next(iter(properties.items()))
    target_properties = target["properties"]
    valid = name in target_properties and name in (target.get("required") or [])
    if not valid or not _valid_const_constraint(constraint):
        raise RefinementError(f"allOf overlay {name!r} must narrow required property")
    value = constraint["const"]
    if not _const_matches(value, target_properties[name]):
        raise RefinementError(f"incompatible const for {name!r}")
    return name, value


def _valid_const_constraint(constraint: object) -> bool:
    if not isinstance(constraint, dict) or "const" not in constraint:
        return False
    return not (set(constraint) - {"const", *_ANNOTATIONS})


def _const_matches(value: Any, schema: dict[str, Any]) -> bool:
    if value is not None and not isinstance(value, (bool, int, float, str)):
        return False
    enum = schema.get("enum")
    if isinstance(enum, list):
        return value in enum
    declared = schema.get("type")
    accepted = declared if isinstance(declared, list) else [declared]
    json_type = _json_type(value)
    return json_type in accepted or (json_type == "integer" and "number" in accepted)


def _json_type(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    return "string"
