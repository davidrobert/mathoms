"""Destilação do exec context (manifest F5 → texto compactado, ADR-200)."""

from __future__ import annotations

import json
from typing import Any, Mapping

from backend.app.services.parecer_manifest import ManifestData
from pipeline.llm.prompts._sanitization import contains_injection_pattern
from pipeline.llm.value_formatter import format_value

# Anti-injection de **saída** (ADR-203 §D9): redação de narrativas E5 destiladas
# no exec context do parecer. Fonte única de "o que é injeção" reconciliada com
# Layer 1 (ADR-175): consome ``contains_injection_pattern`` em vez de regex local.
# Distingue-se da entrada (Layer 1 stripa); aqui redata com marcador.
_MAX_NARRATIVA_CHARS = 500
_TRUNCATION_MARKER = "\n…[exec context truncado em max_exec_context_bytes]"


def _walk_indices(current: Any, indices: list[str]) -> Any:
    """Aplica indices [*] ou [n] sobre current. Wildcard terminal retorna lista."""
    for idx in indices:
        if idx == "*":
            if not isinstance(current, list):
                return None
            return current  # caller pára aqui — wildcard é terminal por convenção
        try:
            current = current[int(idx)]
        except (IndexError, TypeError, ValueError):
            return None
    return current


def _tokenize_part(part: str) -> tuple[str, list[str]]:
    """Tokeniza ``foo[*][0]`` em ``("foo", ["*", "0"])``."""
    base = part
    idxs: list[str] = []
    while "[" in base:
        head, _, tail = base.partition("[")
        idx, _, rest = tail.partition("]")
        idxs.append(idx)
        base = head + rest
    return base, idxs


def walk_path(data: Mapping[str, Any], path: str) -> Any:
    """Resolve JSONPath subset ``$.a.b[*].c`` sobre dict. Retorna None se ausente."""
    if not path.startswith("$."):
        return None
    current: Any = data
    for part in path[2:].split("."):
        base, idxs = _tokenize_part(part)
        if not isinstance(current, Mapping):
            return None
        current = current.get(base)
        current = _walk_indices(current, idxs)
        if isinstance(current, list) and idxs and "*" in idxs:
            return current  # terminou em wildcard
        if current is None:
            return None
    return current


def redact_narrativas_inline(s: Any) -> Any:
    """Sanitiza strings de narrativas (truncate + redact se padrão hostil)."""
    if isinstance(s, str):
        s = s[:_MAX_NARRATIVA_CHARS] + ("…" if len(s) > _MAX_NARRATIVA_CHARS else "")
        if contains_injection_pattern(s):
            return "[REDACTED_SUSPECT_PATTERN]"
        return s
    if isinstance(s, Mapping):
        return {k: redact_narrativas_inline(v) for k, v in s.items()}
    if isinstance(s, list):
        return [redact_narrativas_inline(v) for v in s]
    return s


def _short(value: Any, *, limit: int = 300) -> str:
    """Stringify defensivo — limita tamanho por linha do exec context."""
    if isinstance(value, str):
        s = value
    elif isinstance(value, (int, float, bool)) or value is None:
        s = str(value)
    else:
        s = json.dumps(value, ensure_ascii=False, default=str)
    return s[:limit] + "…" if len(s) > limit else s


def _render_scalar(block: Mapping[str, Any], e5_data: Mapping[str, Any]) -> str:
    path = block.get("path")
    if not path:
        return ""
    value = walk_path(e5_data, path)
    label = block.get("label", path)
    on_null = block.get("on_null", "skip")
    if value is None:
        if on_null == "skip":
            return ""
        return f"- **{label}**: —" if on_null == "placeholder" else f"- **{label}**: (ausente)"
    if path == "$.narrativas":
        value = redact_narrativas_inline(value)
    formatted = format_value(value, block.get("value_format", "raw"))
    return f"- **{label}**: {_short(formatted)}"


def _render_key_value(block: Mapping[str, Any], e5_data: Mapping[str, Any]) -> str:
    title = block.get("title", "")
    on_null = block.get("on_null", "skip")
    lines = [f"**{title}**:"] if title else []
    for f in block.get("fields", []):
        v = walk_path(e5_data, f["path"])
        if v is None and on_null == "skip":
            continue
        formatted = format_value(v, f.get("format", "raw"))
        lines.append(f"  - {f.get('label', f['path'])}: {_short(formatted)}")
    return "\n".join(lines)


def _render_row(row: Mapping[str, Any], cols: list[dict]) -> str:
    cells = []
    for col in cols:
        v = row.get(col["path"])
        fv = format_value(v, col.get("format", "raw"))
        cells.append(f"{col.get('label', col['path'])}={_short(fv)}")
    return "  - " + " · ".join(cells)


def _render_table(block: Mapping[str, Any], e5_data: Mapping[str, Any]) -> str:
    path = block.get("path")
    rows = walk_path(e5_data, path) if path else None
    if not isinstance(rows, list):
        return ""
    max_rows = int(block.get("max_rows", 10))
    cols = block.get("columns", [])
    title = block.get("title", "")
    out = [f"**{title}** (top {min(len(rows), max_rows)}):"] if title else []
    for row in rows[:max_rows]:
        if isinstance(row, Mapping):
            out.append(_render_row(row, cols))
    return "\n".join(out)


def render_block(block: Mapping[str, Any], e5_data: Mapping[str, Any]) -> str:
    """Renderiza um block do manifest para texto plano (despacha por format)."""
    fmt = block.get("format")
    if fmt == "scalar":
        return _render_scalar(block, e5_data)
    if fmt == "key_value":
        return _render_key_value(block, e5_data)
    if fmt == "table":
        return _render_table(block, e5_data)
    return ""


def _render_section(section: dict, e5_data: Mapping[str, Any]) -> list[str]:
    """Renderiza header + blocks + hints de uma seção."""
    parts: list[str] = [f"### {section.get('title', section.get('id', ''))}"]
    for block in section.get("blocks", []):
        rendered = render_block(block, e5_data)
        if rendered:
            parts.append(rendered)
    for hint in section.get("narrative_hints", []) or []:
        parts.append(f"_hint:_ {hint}")
    parts.append("")
    return parts


def distill_exec_context(manifest: ManifestData, e5_data: Mapping[str, Any]) -> str:
    """Aplica manifest sobre E5 → texto destilado (≤ ``max_exec_context_bytes``)."""
    parts: list[str] = []
    for section in manifest.sections:
        parts.extend(_render_section(section, e5_data))
    body = "\n".join(parts)
    cap = manifest.max_exec_context_bytes
    if len(body.encode("utf-8")) > cap:
        body = body.encode("utf-8")[:cap].decode("utf-8", errors="ignore") + _TRUNCATION_MARKER
    return body
