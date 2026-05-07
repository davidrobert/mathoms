"""Render de slug + frontmatter + body para dev/split_adrs.py (ADR-182, F2.A)."""
# Módulo privado de dev/split_adrs.py — separado para manter o entrypoint
# abaixo do limite de 500 linhas (P2_long_files no audit code-style).
# Public API: title_slug, filename_for, render_note.

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

MAX_SLUG_LEN = 50


@dataclass
class AdrBlock:
    """Bloco de uma ADR no source: heading + body raw."""

    id: str
    num: str
    suffix: str | None
    title: str
    start_line: int
    body_lines: list[str]


@dataclass
class AdrMeta:
    """Metadados extraídos do body de uma ADR."""

    status: str
    phase: str | None
    date: str
    relates_to: list[str]
    supersedes: list[str]
    superseded_by: list[str]
    warnings: list[str]


# ----------------------------------------------------------------------
# Slug (filename body)
# ----------------------------------------------------------------------


def _github_slug(text: str) -> str:
    """Replica github_slug: lowercase + remove non-[\\w\\- ] + espaço→hífen."""
    s = text.lower()
    s = re.sub(r"[^\w\- ]+", "", s, flags=re.UNICODE)
    return s.replace(" ", "-")


def _ascii_translit(s: str) -> str:
    """NFKD + drop combining marks → ASCII puro."""
    normalized = unicodedata.normalize("NFKD", s)
    return normalized.encode("ascii", "ignore").decode("ascii")


def _normalize_slug_body(slug: str) -> str:
    """Aplica translit ASCII, troca `_` por `-`, comprime hífens, remove bordas."""
    s = _ascii_translit(slug).replace("_", "-")
    s = re.sub(r"[^a-z0-9-]", "", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s


def _truncate_at_word_boundary(slug: str, max_len: int) -> str:
    """Trunca em `max_len` preferindo cortar num hífen (boundary de palavra)."""
    if len(slug) <= max_len:
        return slug
    truncated = slug[:max_len].rstrip("-")
    idx = truncated.rfind("-")
    if idx >= max_len // 2:
        return truncated[:idx]
    return truncated


def title_slug(title: str, max_len: int = MAX_SLUG_LEN) -> str:
    """Gera slug body do filename a partir do título da ADR."""
    raw = _github_slug(title)
    body = _normalize_slug_body(raw)
    return _truncate_at_word_boundary(body, max_len)


def filename_for(block: AdrBlock, slug_body: str) -> str:
    """Compõe `NNN-<slug>.md` ou `NNN-x-<slug>.md` para sufixo legado."""
    prefix = f"{block.num}-{block.suffix.lower()}-" if block.suffix else f"{block.num}-"
    return f"{prefix}{slug_body}.md"


# ----------------------------------------------------------------------
# Frontmatter render
# ----------------------------------------------------------------------


def _yaml_string(value: str) -> str:
    """Escapa string para YAML inline (aspas duplas, escape de `"` e `\\`)."""
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _yaml_list(items: list[str]) -> str:
    """Renderiza lista YAML inline com aspas duplas (evita coerção de wikilinks)."""
    if not items:
        return "[]"
    quoted = ", ".join(f'"{item}"' for item in items)
    return f"[{quoted}]"


def _aliases_for(adr_id: str) -> list[str]:
    """Mínimo: ['ADR NNN'] para autocomplete (variante sem hífen)."""
    return [adr_id.replace("-", " ", 1)]


def _tags_for(status: str) -> list[str]:
    """Tags hierárquicas: type/adr + status/<status-lower>."""
    return ["type/adr", f"status/{status.lower()}"]


def _scalar_fm_lines(block: AdrBlock, meta: AdrMeta) -> list[str]:
    """Linhas escalares do frontmatter (id/type/title/status[/phase]/date)."""
    out = [
        f"id: {block.id}",
        "type: adr",
        f"title: {_yaml_string(block.title)}",
        f"status: {meta.status}",
    ]
    if meta.phase:
        out.append(f"phase: {_yaml_string(meta.phase)}")
    out.append(f'date: "{meta.date}"')
    return out


def _list_fm_lines(block: AdrBlock, meta: AdrMeta) -> list[str]:
    """Linhas de lista do frontmatter (relates_to/supersedes/.../aliases/tags)."""
    lines = [
        f"relates_to: {_yaml_list(meta.relates_to)}",
        f"supersedes: {_yaml_list(meta.supersedes)}",
        f"superseded_by: {_yaml_list(meta.superseded_by)}",
        f"aliases: {_yaml_list(_aliases_for(block.id))}",
        "tags:",
    ]
    for tag in _tags_for(meta.status):
        lines.append(f"  - {tag}")
    return lines


def _frontmatter_lines(block: AdrBlock, meta: AdrMeta, body_text: str) -> list[str]:
    """Renderiza o bloco YAML de frontmatter completo (delimitadores incluídos)."""
    return [
        "---",
        *_scalar_fm_lines(block, meta),
        *_list_fm_lines(block, meta),
        f"size_lines: {body_text.count(chr(10)) + 1}",
        "---",
    ]


# ----------------------------------------------------------------------
# Body render
# ----------------------------------------------------------------------


def _trim_body(body_lines: list[str]) -> list[str]:
    """Remove blank lines + `---` separador no início/fim, preservando o meio."""
    start = 0
    while start < len(body_lines) and body_lines[start].strip() == "":
        start += 1
    end = len(body_lines)
    while end > start and body_lines[end - 1].strip() == "":
        end -= 1
    # Body do source termina com `---` separador antes da próxima ADR; descarta.
    while end > start and body_lines[end - 1].strip() == "---":
        end -= 1
    while end > start and body_lines[end - 1].strip() == "":
        end -= 1
    return body_lines[start:end]


def render_note(block: AdrBlock, meta: AdrMeta) -> str:
    """Constrói o conteúdo final do arquivo .md (frontmatter + H1 + body)."""
    body_inner = _trim_body(block.body_lines)
    body_text_for_size = "\n".join(
        ["", f"# {block.id} — {block.title}", "", *body_inner, ""],
    )
    fm_lines = _frontmatter_lines(block, meta, body_text_for_size)
    out_lines = [*fm_lines, "", f"# {block.id} — {block.title}", "", *body_inner, ""]
    return "\n".join(out_lines)
