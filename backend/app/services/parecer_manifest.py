"""Loaders do manifest + persona do parecer planejador (ADR-200/201)."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

_MANIFEST_PATH = "config/prompts/parecer_planejador.yaml"
_PERSONA_PATH = "config/agents/planner_persona.md"


@dataclass(frozen=True)
class CitationCatalogConfig:
    """Intenção declarativa do catálogo de citação (A26.l1 · ADR-279 §E)."""

    emit: bool = False
    fmt: str = "flat_path_list"
    monetary_only: bool = True
    max_entries: int = 30
    max_bytes: int = 1600


@dataclass(frozen=True)
class CitationLabel:
    """Entrada do mapa path → rótulo (A40.l49 · ADR-296)."""

    rotulo_id: str
    label: str


@dataclass
class ManifestData:
    """Manifest parseado — subset consumido pelo orchestrator."""

    version: str
    sections: list[dict]
    tools_section_whitelist: frozenset[str]
    format_hints: dict[str, str]
    max_tool_iterations: int
    max_total_input_tokens: int
    max_exec_context_bytes: int
    evidencia_verification_mode: str = "warn"
    citation_catalog: CitationCatalogConfig = field(default_factory=CitationCatalogConfig)
    citation_labels: dict[str, CitationLabel] = field(default_factory=dict)


def _resolve_repo_path(rel: str) -> Path:
    """Localiza arquivo relativo à raiz do repo independente de cwd."""
    candidates = [Path(rel), Path(__file__).resolve().parents[3] / rel]
    for p in candidates:
        if p.is_file():
            return p
    raise FileNotFoundError(f"file not found: {rel} (tried {candidates})")


def _extract_section_whitelist(tools: list[dict]) -> frozenset[str]:
    """Whitelist de section enums declaradas em ``tools[].args_schema.section.enum``."""
    whitelist: set[str] = set()
    for tool in tools:
        if tool.get("name") == "get_e5_section":
            enum = tool.get("args_schema", {}).get("section", {}).get("enum", [])
            whitelist.update(enum)
    return frozenset(whitelist)


def _extract_block_format_hints(block: dict, fmt_hints: dict[str, str]) -> None:
    """Coleta format hints de um único block (scalar/table/key_value)."""
    path_key = block.get("path")
    value_fmt = block.get("value_format")
    if path_key and value_fmt:
        fmt_hints[path_key] = value_fmt
    for col in block.get("columns", []) or []:
        col_path, col_fmt = col.get("path"), col.get("format")
        if col_path and col_fmt:
            fmt_hints[col_path] = col_fmt
    for fld in block.get("fields", []) or []:
        fpath, ffmt = fld.get("path"), fld.get("format")
        if fpath and ffmt:
            fmt_hints[fpath] = ffmt


def _extract_format_hints(sections: list[dict]) -> dict[str, str]:
    """Mapeia ``path → fmt`` cruzando todos os blocks do manifest."""
    fmt_hints: dict[str, str] = {}
    for section in sections:
        for block in section.get("blocks", []):
            _extract_block_format_hints(block, fmt_hints)
    return fmt_hints


def _parse_citation_catalog(raw: dict) -> CitationCatalogConfig:
    """Lê o bloco citation_catalog; ausente = emit desligado (pré-A26)."""
    cc = raw.get("citation_catalog") or {}
    return CitationCatalogConfig(
        emit=bool(cc.get("emit", False)),
        fmt=str(cc.get("format", "flat_path_list")),
        monetary_only=bool(cc.get("monetary_only", True)),
        max_entries=int(cc.get("max_entries", 30)),
        max_bytes=int(cc.get("max_bytes", 1600)),
    )


def _parse_one_citation_label(path: object, spec: object) -> CitationLabel:
    if not isinstance(path, str) or not path.startswith("$."):
        raise ValueError(f"citation_labels key must be JSONPath, got {path!r}")
    if not isinstance(spec, dict):
        raise ValueError(f"citation_labels[{path!r}] expected mapping, got {type(spec).__name__}")
    rotulo_id = spec.get("rotulo_id")
    label = spec.get("label")
    if not isinstance(rotulo_id, str) or not rotulo_id.isidentifier() or len(rotulo_id) > 64:
        raise ValueError(f"citation_labels[{path!r}].rotulo_id must be identifier ≤64")
    if not isinstance(label, str) or not label.strip() or len(label) > 64:
        raise ValueError(f"citation_labels[{path!r}].label must be 1..64 chars")
    return CitationLabel(rotulo_id=rotulo_id, label=label.strip())


def _parse_citation_labels(raw: dict) -> dict[str, CitationLabel]:
    block = raw.get("citation_labels") or {}
    if not isinstance(block, dict):
        raise ValueError(f"citation_labels must be a mapping, got {type(block).__name__}")
    return {path: _parse_one_citation_label(path, spec) for path, spec in block.items()}


def load_manifest(path: Optional[str] = None) -> ManifestData:
    """Lê manifest YAML e expõe os campos consumidos pelo orchestrator."""
    import yaml

    p = _resolve_repo_path(path or _MANIFEST_PATH)
    raw = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    sections = list(raw.get("context_sections", []))
    return ManifestData(
        version=str(raw.get("version", "0.0")),
        sections=sections,
        tools_section_whitelist=_extract_section_whitelist(raw.get("tools", [])),
        format_hints=_extract_format_hints(sections),
        max_tool_iterations=int(raw.get("max_tool_iterations", 6)),
        max_total_input_tokens=int(raw.get("max_total_input_tokens", 50_000)),
        max_exec_context_bytes=int(raw.get("max_exec_context_bytes", 5120)),
        evidencia_verification_mode=str(raw.get("evidencia_verification_mode", "warn")),
        citation_catalog=_parse_citation_catalog(raw),
        citation_labels=_parse_citation_labels(raw),
    )


def load_persona(path: Optional[str] = None) -> tuple[str, str]:
    """Lê persona markdown + computa SHA-256 (auditoria, ADR-201)."""
    p = _resolve_repo_path(path or _PERSONA_PATH)
    body = p.read_text(encoding="utf-8")
    return body, hashlib.sha256(body.encode("utf-8")).hexdigest()
