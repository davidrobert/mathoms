"""Loaders do manifest + persona do parecer planejador (ADR-200/201)."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

_MANIFEST_PATH = "config/prompts/parecer_planejador.yaml"
_PERSONA_PATH = "config/agents/planner_persona.md"


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
    )


def load_persona(path: Optional[str] = None) -> tuple[str, str]:
    """Lê persona markdown + computa SHA-256 (auditoria, ADR-201)."""
    p = _resolve_repo_path(path or _PERSONA_PATH)
    body = p.read_text(encoding="utf-8")
    return body, hashlib.sha256(body.encode("utf-8")).hexdigest()
