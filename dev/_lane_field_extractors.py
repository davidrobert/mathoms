"""Helpers de extração de campos de body/title para dev/migrate_lanes.py."""
# Status, datas, PR, branch slug, ADRs, prioridade — derivados via regex
# tolerante sobre o body Markdown da lane no BACKLOG legado.

from __future__ import annotations

import re

_SHIP_DATE_RE = re.compile(r"entregue\s+(\d{4}-\d{2}-\d{2})")
_PR_RE = re.compile(r"PR\s+#(\d{1,5})|\(#(\d{1,5})\)|\[#(\d{1,5})\]")
_BRANCH_RE = re.compile(r"agent/([a-z][a-z0-9-]*)/")
_ADR_RE = re.compile(r"ADR-(\d{3})")
_PRIORITY_RE = re.compile(r"\bP[012]\b")


def extract_status(body: str, raw_title: str) -> str:
    """Deriva status a partir de marcadores ✅/🚧/❌/⏸ no body + título."""
    haystack = f"{raw_title}\n{body}"
    if _is_cancelled(haystack):
        return "cancelled"
    if _is_shipped_title(raw_title):
        return "shipped"
    if "🚧" in haystack:
        return "in_progress"
    if _is_blocked(haystack):
        return "blocked"
    if _is_shipped_body(haystack):
        return "shipped"
    return "open"


def _is_cancelled(haystack: str) -> bool:
    return "❌" in haystack and ("Cancelada" in haystack or "Descartado" in haystack)


def _is_shipped_title(raw_title: str) -> bool:
    return "✅ entregue" in raw_title or " entregue " in raw_title


def _is_blocked(haystack: str) -> bool:
    return "⏸" in haystack and "aguarda" in haystack.lower()


def _is_shipped_body(haystack: str) -> bool:
    if "✅ entregue" in haystack or "✅ fechad" in haystack.lower():
        return True
    return "✅" in haystack


def extract_ship_date(body: str, raw_title: str) -> str | None:
    """Primeira data ISO após `entregue` no body ou título."""
    m = _SHIP_DATE_RE.search(f"{raw_title}\n{body}")
    return m.group(1) if m else None


def extract_ship_pr(body: str) -> int | None:
    """Primeiro PR plausível (#NNN com ≥2 dígitos)."""
    for m in _PR_RE.finditer(body):
        plausible = next((g for g in m.groups() if g and len(g) >= 2), None)
        if plausible:
            return int(plausible)
    return None


def extract_branch_slug(body: str) -> str | None:
    """Primeira `agent/<slug>/` mencionada no body."""
    m = _BRANCH_RE.search(body)
    return m.group(1) if m else None


def extract_adrs(body: str) -> list[str]:
    """Wikilinks únicos `[[ADR-NNN]]` ordenados pelo número."""
    nums = sorted({m.group(1) for m in _ADR_RE.finditer(body)})
    return [f"[[ADR-{n}]]" for n in nums]


def extract_priority(body: str, raw_title: str) -> str | None:
    """Prioridade explícita (P0/P1/P2) — primeira ocorrência."""
    m = _PRIORITY_RE.search(f"{raw_title}\n{body}")
    return m.group(0) if m else None


def clean_title(raw_title: str) -> str:
    """Remove sufixo `✅ entregue ...`/`🚧 ...` do title; mantém propósito."""
    title = re.split(r"\s+(?:✅|🚧|❌|⏸)", raw_title, maxsplit=1)[0]
    return title.strip().rstrip(",")


_SLUG_NOISE_TOKENS = {
    "entregue",
    "shipped",
    "delivered",
    "concluído",
    "concluida",
    "concluido",
    "concluída",
    "✅",
    "🚧",
    "❌",
    "⏸",
    "deprecated",
    "wip",
}

_SLUG_MAX_TOKENS = 7

_ACCENT_MAP: tuple[tuple[str, str], ...] = (
    ("[áàâãä]", "a"),
    ("[éèêë]", "e"),
    ("[íìîï]", "i"),
    ("[óòôõö]", "o"),
    ("[úùûü]", "u"),
    ("[ç]", "c"),
)


def _strip_accents(text: str) -> str:
    for src, repl in _ACCENT_MAP:
        text = re.sub(src, repl, text)
    return text


def slugify(text: str) -> str:
    """Slug ASCII lowercase + hyphen, truncado a N tokens; remove noise tokens."""
    text = _strip_accents(text.lower())
    text = re.sub(r"\([^)]*\)", " ", text)
    text = re.sub(r"\b\d{4}-\d{2}-\d{2}\b", " ", text)
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    tokens = [t for t in text.split("-") if t and t not in _SLUG_NOISE_TOKENS]
    return "-".join(tokens[:_SLUG_MAX_TOKENS]) or "lane"
