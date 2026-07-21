"""Destilação do exec context (manifest F5 → texto compactado, ADR-200)."""

from __future__ import annotations

import json
from typing import Any, Iterator, Mapping

from backend.app.services.parecer_citation_catalog import (
    build_citation_catalog,
    render_citation_catalog,
)
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


def _flatten_leaves(value: Any, prefix: str = "") -> Iterator[tuple[str, Any]]:
    """Achata dict/list em pares (chave_pontilhada, folha escalar). Cada folha é
    curta e sobrevive ao ``_short(300)`` individualmente — evita a truncação do
    dump raw que cortava os zeros estruturais no fim (PE-01)."""
    if not isinstance(value, (Mapping, list)):
        yield (prefix or "valor", value)
        return
    is_list = isinstance(value, list)
    items = enumerate(value) if is_list else value.items()
    for k, v in items:
        child = f"{prefix}[{k}]" if is_list else (f"{prefix}.{k}" if prefix else str(k))
        yield from _flatten_leaves(v, child)


def _render_field(field: Mapping[str, Any], value: Any) -> list[str]:
    """Uma linha por folha; dict/list é achatado (PE-01), escalar mantém o label.
    Folha None é ausência (A37.l4) — pulada, paridade com on_null:skip escalar."""
    if isinstance(value, (Mapping, list)):
        return [
            f"  - {leaf}: {_short(val)}" for leaf, val in _flatten_leaves(value) if val is not None
        ]
    formatted = format_value(value, field.get("format", "raw"))
    return [f"  - {field.get('label', field['path'])}: {_short(formatted)}"]


def _render_key_value(block: Mapping[str, Any], e5_data: Mapping[str, Any]) -> str:
    on_null = block.get("on_null", "skip")
    field_lines: list[str] = []
    for f in block.get("fields", []):
        v = walk_path(e5_data, f["path"])
        if v is None and on_null == "skip":
            continue
        field_lines.extend(_render_field(f, v))
    # Seção ausente (ex.: $.irpf_kpis num workspace sem IRPF, ADR-157) → NENHUM
    # campo sobrevive: omite o bloco inteiro (preserva a semântica on_null:skip do
    # scalar antigo; sem cabeçalho órfão prometendo dado inexistente).
    if not field_lines:
        return ""
    title = block.get("title", "")
    return "\n".join(([f"**{title}**:"] if title else []) + field_lines)


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


def _render_catalog_block(manifest: ManifestData, e5_data: Mapping[str, Any]) -> str:
    """Catálogo de citação (A26.l1) — vazio se emit desligado."""
    cfg = manifest.citation_catalog
    if not cfg.emit:
        return ""
    entries = build_citation_catalog(
        e5_data, section_whitelist=manifest.tools_section_whitelist, max_entries=cfg.max_entries
    )
    return render_citation_catalog(entries, max_bytes=cfg.max_bytes)


def distill_exec_context(manifest: ManifestData, e5_data: Mapping[str, Any]) -> str:
    """Aplica manifest sobre E5 → texto destilado + catálogo de citação (A26.l1)."""
    parts: list[str] = []
    for section in manifest.sections:
        parts.extend(_render_section(section, e5_data))
    body = "\n".join(parts)
    cap = manifest.max_exec_context_bytes
    if len(body.encode("utf-8")) > cap:
        body = body.encode("utf-8")[:cap].decode("utf-8", errors="ignore") + _TRUNCATION_MARKER
    # Catálogo tem orçamento próprio (cfg.max_bytes), anexado APÓS o cap das
    # narrativas — nunca truncado por elas (prompt-engineer 2026-06-16).
    catalog = _render_catalog_block(manifest, e5_data)
    return f"{body}\n\n{catalog}" if catalog else body
