"""Renderer do ADR_INDEX.md — agrupamento por categoria + status (extraído de build_doc_index.py)."""

# Mantém build_doc_index.py <500 linhas (guideline CLAUDE.md). Recebe notas via
# Protocol estrutural (AdrLike) — não importa Note do orquestrador, evita ciclo.
# F2.F deletará dev/build_adr_toc.py; constantes em dev/_adr_categories_legacy.py.

from __future__ import annotations

import re
from typing import Any, Callable, Protocol

try:
    from _adr_categories_legacy import CATEGORIES_LEGACY, OVERRIDES_LEGACY
except ModuleNotFoundError:  # pragma: no cover — só quando importado como dev._adr_index_renderer
    from dev._adr_categories_legacy import CATEGORIES_LEGACY, OVERRIDES_LEGACY

ADR_STATUS_ORDER: tuple[str, ...] = ("Decidido", "Proposto", "Roadmap")
ADR_ID_RE = re.compile(r"ADR-(\d+)")
_ADR_INDEX_TITLE = "ADR_INDEX — Índice de Architectural Decision Records"
_ADR_INDEX_FOOTER = ("---", "> Regenerar: `python3 dev/build_doc_index.py --inline`")


class AdrLike(Protocol):
    """Duck-type para Note: tudo que o renderer precisa ler."""

    id: str
    title: str
    status: str
    tags: tuple[str, ...]
    raw: dict[str, Any]


def _load_adr_categories() -> tuple[list[tuple[str, list[str], list[range]]], dict[int, str]]:
    """Retorna (CATEGORIES_LEGACY, OVERRIDES_LEGACY) — wrapper para mock em testes."""
    return CATEGORIES_LEGACY, OVERRIDES_LEGACY


def _adr_num_from_id(adr_id: str) -> int | None:
    """Extrai o número da ADR a partir de id `ADR-NNN`. None se não casa."""
    match = ADR_ID_RE.match(adr_id)
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def _category_via_legacy(num: int, title: str, categories: list, overrides: dict) -> str | None:
    """Aplica overrides + heurística legada (keywords/ranges); None se nenhum match."""
    if num in overrides:
        return overrides[num]
    title_lower = title.lower()
    for cat, keywords, ranges in categories:
        if any(kw in title_lower for kw in keywords) or any(num in r for r in ranges):
            return cat
    return None


def _category_via_tag(tags: tuple[str, ...]) -> str | None:
    """Primeira tag `area/*` como categoria; None se nenhuma."""
    for tag in tags:
        if tag.startswith("area/"):
            return tag.removeprefix("area/")
    return None


def category_for_adr(note: AdrLike) -> str:
    """Categoriza ADR via fallback hierárquico: override → tag area/* → "Outras"."""
    categories, overrides = _load_adr_categories()
    num = _adr_num_from_id(note.id)
    if num is not None:
        legacy = _category_via_legacy(num, note.title, categories, overrides)
        if legacy is not None:
            return legacy
    return _category_via_tag(note.tags) or "Outras"


def _ordered_categories(present: set[str]) -> list[str]:
    """Ordena categorias presentes seguindo CATEGORIES_LEGACY + tags + 'Outras' no fim."""
    canonical = [c[0] for c in CATEGORIES_LEGACY]
    seen = set(canonical)
    out = [c for c in canonical if c in present]
    extra = sorted(c for c in present if c not in seen and c != "Outras")
    out.extend(extra)
    if "Outras" in present:
        out.append("Outras")
    return out


def _adr_sort_key(note: AdrLike) -> tuple[int, str]:
    """Ordena ADRs por número ascendente; id como tiebreaker estável."""
    num = _adr_num_from_id(note.id)
    return (num if num is not None else 10**9, note.id)


def _format_adr_line(note: AdrLike) -> str:
    """Linha por ADR no índice: wikilink + título + (opcional) phase."""
    phase_raw = note.raw.get("phase")
    phase = str(phase_raw).strip() if phase_raw not in (None, "") else ""
    suffix = f" · phase {phase}" if phase else ""
    return f"- [[{note.id}]] — {note.title}{suffix}"


def _status_summary_lines(adrs: list[AdrLike]) -> list[str]:
    """Bloco "Sumário por status" com contagens canônicas + outros."""
    by_status: dict[str, int] = {}
    for note in adrs:
        by_status[note.status] = by_status.get(note.status, 0) + 1
    out = ["## Sumário por status", ""]
    for status in ADR_STATUS_ORDER:
        out.append(f"- **{status}**: {by_status.get(status, 0)}")
    extras = sorted(s for s in by_status if s not in ADR_STATUS_ORDER and s)
    out.extend(f"- **{status}**: {by_status[status]}" for status in extras)
    out.append("")
    return out


def _adr_range_label(adrs: list[AdrLike]) -> str:
    """Texto descritivo do range de ADRs (ex.: 'ADR-001 a ADR-182') ou id único."""
    nums = sorted(n for n in (_adr_num_from_id(a.id) for a in adrs) if n is not None)
    if not nums:
        return ""
    if len(nums) == 1:
        return f"ADR-{nums[0]:03d}"
    return f"ADR-{nums[0]:03d} a ADR-{nums[-1]:03d}"


def _render_category_block(category: str, notes_in_cat: list[AdrLike]) -> list[str]:
    """Renderiza uma categoria com sub-blocos por status."""
    out: list[str] = [f"## {category}", ""]
    by_status: dict[str, list[AdrLike]] = {}
    for note in notes_in_cat:
        by_status.setdefault(note.status or "(sem status)", []).append(note)
    status_order = [s for s in ADR_STATUS_ORDER if s in by_status]
    extras = sorted(s for s in by_status if s not in ADR_STATUS_ORDER)
    for status in status_order + extras:
        bucket = sorted(by_status[status], key=_adr_sort_key)
        out.extend((f"### {status} ({len(bucket)})", ""))
        out.extend(_format_adr_line(n) for n in bucket)
        out.append("")
    return out


def _adr_count_line(adrs: list[AdrLike]) -> str:
    """Linha 'N ADRs (ADR-XXX a ADR-YYY) em docs/adr/.' (ou singular)."""
    range_label = _adr_range_label(adrs)
    range_suffix = f" ({range_label})" if range_label else ""
    noun = "ADR" if len(adrs) == 1 else "ADRs"
    return f"{len(adrs)} {noun}{range_suffix} em [`docs/adr/`](../../adr/)."


def render_adr_index(adrs: list[AdrLike], header_fn: Callable[[str], list[str]]) -> list[str]:
    """Monta as linhas do ADR_INDEX.md. `header_fn(title)` produz cabeçalho de aviso + h1."""
    lines = header_fn(_ADR_INDEX_TITLE)
    lines.extend(("Volta para [`00-INDEX`](../00-INDEX.md).", ""))
    if not adrs:
        lines.append(
            "_0 ADRs migradas para a vault ainda (Fase 2 do plano DOC_REORG popula 175+)._"
        )
        lines.extend(("", *_ADR_INDEX_FOOTER))
        return lines
    lines.extend((_adr_count_line(adrs), ""))
    lines.extend(_status_summary_lines(adrs))
    by_cat: dict[str, list[AdrLike]] = {}
    for note in adrs:
        by_cat.setdefault(category_for_adr(note), []).append(note)
    for category in _ordered_categories(set(by_cat)):
        lines.extend(_render_category_block(category, by_cat[category]))
    lines.extend(_ADR_INDEX_FOOTER)
    return lines
