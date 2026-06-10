"""Telemetria estruturada de drift de schema-validation (ADR-284) — 1 record WARNING por path distinto, sem nunca logar ``error.message``/``error.instance`` (jsonschema embute o valor ofensor; redaction por key não pega)."""

from __future__ import annotations

import logging
from typing import Any, Dict, Mapping, Optional

_validation_telemetry_logger = logging.getLogger("mathoms.pipeline.schema_validation")

# Teto de segurança de records por artefato (ADR-284). A unidade de contagem é
# o par (validation_path, validator) deduplicado — o cap quase nunca dispara.
_TELEMETRY_MAX_PATHS = 20


def _validation_paths(error: Any) -> list[str]:
    """Paths normalizados (índices→``[]``); additionalProperties/required expandem 1 path por campo (nome de campo é metadado, não PII — ADR-284)."""
    base = "$"
    for part in error.absolute_path:
        base += "[]" if isinstance(part, int) else f".{part}"
    if not isinstance(error.instance, dict):
        return [base]
    if error.validator == "additionalProperties" and isinstance(error.schema, dict):
        extras = sorted(set(error.instance) - set(error.schema.get("properties", {})))
        if extras:
            return [f"{base}.{field}" for field in extras]
    if error.validator == "required" and isinstance(error.validator_value, list):
        missing = sorted(set(error.validator_value) - set(error.instance))
        if missing:
            return [f"{base}.{field}" for field in missing]
    return [base]


def _count_drift_paths(errors: list) -> Dict[tuple, int]:
    counts: Dict[tuple, int] = {}
    for error in errors:
        for path in _validation_paths(error):
            pair = (path, str(error.validator))
            counts[pair] = counts.get(pair, 0) + 1
    return counts


def _emit_drift_records(counts: Dict[tuple, int], base_extra: Dict[str, Any]) -> None:
    for (path, validator_keyword), n in list(counts.items())[:_TELEMETRY_MAX_PATHS]:
        _validation_telemetry_logger.warning(
            "schema_validation_drift",
            extra={
                **base_extra,
                "validation_path": path,
                "validator_keyword": validator_keyword,
                "occurrence_count": n,
            },
        )
    if len(counts) > _TELEMETRY_MAX_PATHS:
        _validation_telemetry_logger.warning(
            "schema_validation_drift_truncated",
            extra={**base_extra, "distinct_paths": len(counts), "emitted": _TELEMETRY_MAX_PATHS},
        )


def _base_extra(
    schema_name: str, source: str, mode: str, context: Optional[Mapping[str, str]] = None
) -> Dict[str, Any]:
    extra: Dict[str, Any] = {
        "schema_name": schema_name,
        "artifact_source": source,
        "mode": mode,
        "outcome": "warn" if mode == "warn" else "reject",
    }
    if context:
        extra.update({k: str(v) for k, v in context.items() if v is not None})
    return extra


def handle_validation_failure(
    errors: list,
    *,
    source: str,
    schema_name: str,
    mode: str,
    context: Optional[Mapping[str, str]] = None,
) -> bool:
    """Telemetria (1 record por path distinto) + log humano via ``log_stage``; retorna ``True`` apenas em modo ``warn``."""
    import scripts.pipeline_common as _pc

    counts = _count_drift_paths(errors)
    _emit_drift_records(counts, _base_extra(schema_name, source, mode, context))
    paths_preview = ", ".join(sorted({p for p, _ in counts})[:5])
    _pc.log_stage(
        "WARN" if mode == "warn" else "ERROR",
        f"Schema validation falhou para {source} ({schema_name}): "
        f"{len(counts)} path(s) em drift: {paths_preview}",
    )
    return mode == "warn"
