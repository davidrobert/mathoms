#!/usr/bin/env python3
"""Helpers de extração para `migrate_changelog.py` (ADR-182, F5.A)."""
# Funções puras (sem estado): extraem date, sprint, lane, ADRs, PRs, commits,
# scope a partir de title/body de uma entrada do CHANGELOG.

from __future__ import annotations

import re

# ----------------------------------------------------------------------
# Regexes
# ----------------------------------------------------------------------

INLINE_DATE_RE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
ADR_REF_RE = re.compile(r"\bADR-(\d{3})\b")
PR_REF_RE = re.compile(r"#(\d{1,4})\b")
COMMIT_BACKTICK_RE = re.compile(r"`([0-9a-f]{7,12})`")
LANE_REF_RE = re.compile(r"\b([AFW]\d+\.\d+[a-z]?)\b")
BREAKING_RE = re.compile(r"\bBREAKING\b")

# Datas-default por sprint conhecidas (close date).
SPRINT_DEFAULT_DATE: dict[str, str] = {
    "A7": "2026-04-27",
    "A8": "2026-05-06",
    "A9": "2026-05-04",
    "A10": "2026-05-07",
    "A11": "2026-05-06",
    "F0": "2026-04-12",
    "F1": "2026-04-13",
    "F2": "2026-04-14",
    "F3": "2026-04-14",
    "F4": "2026-04-14",
    "F45": "2026-04-14",
    "F5": "2026-04-14",
    "F6": "2026-04-14",
    "F65": "2026-04-15",
    "F7": "2026-04-15",
    "F8": "2026-04-15",
    "F9": "2026-04-15",
}

WAVE_TO_SPRINT: dict[str, str | None] = {
    "W1": "A11",
    "W2": "A11",
    "W3": "A11",
    "W4": "A11",
    "W5": "W5",
    "W6": "W6",
}


# ----------------------------------------------------------------------
# Date / sprint
# ----------------------------------------------------------------------


def extract_date_from_text(text: str) -> str | None:
    """Captura primeira data ISO em texto. Ignora datas em paths (`/.../2026-04-15/...`)."""
    for m in INLINE_DATE_RE.finditer(text):
        if _is_date_in_path(text, m.start(), m.end()):
            continue
        return m.group(1)
    return None


def _is_date_in_path(text: str, start: int, end: int) -> bool:
    """True se a data aparece dentro de um path (precedida ou seguida por `/`)."""
    before = text[max(0, start - 1) : start]
    after = text[end : end + 1]
    return before == "/" or after == "/"


def sprint_default_date(sprint: str | None) -> str | None:
    """Data-default conhecida para sprint, ou None."""
    if sprint is None:
        return None
    return SPRINT_DEFAULT_DATE.get(sprint)


def normalize_sprint(sprint: str | None) -> str | None:
    """Remove pontos do sprint id (`F4.5` → `F45`)."""
    if sprint is None:
        return None
    return sprint.replace(".", "")


def infer_sprint_from_title_strict(title: str) -> str | None:
    """Lane-id explícita no início do título → sprint correspondente."""
    m = re.match(r"^([AFW]\d+)\.\d+", title)
    if m:
        return m.group(1)
    m = re.match(r"^\[([AFW]\d+(?:\.\d+)?)\]", title)
    if m:
        return m.group(1).split(".")[0]
    m = re.match(r"^Sprint\s+([AF]\d+)", title)
    if m:
        return m.group(1)
    m = re.search(r"\b(W\d+)-T\d+", title)
    if m:
        return WAVE_TO_SPRINT.get(m.group(1))
    return None


def infer_sprint_from_full(text: str) -> str | None:
    """Heurística sobre texto inteiro: `Sprint A10`, `(A10.2)`, `F9.2`, `W1-T02`."""
    m = re.search(r"\bSprint\s+([AF]\d+)", text)
    if m:
        return m.group(1)
    m = re.search(r"\b([AF]\d+)\.\d+", text)
    if m:
        return m.group(1)
    m = re.search(r"\b(W\d+)-T\d+", text)
    if m:
        return WAVE_TO_SPRINT.get(m.group(1))
    return None


# ----------------------------------------------------------------------
# ADR / PR / commit
# ----------------------------------------------------------------------


def extract_adrs(text: str) -> list[str]:
    """Wikilinks `[[ADR-NNN]]` únicos, ordenados por número."""
    nums = sorted({int(m) for m in ADR_REF_RE.findall(text)})
    return [f"[[ADR-{n:03d}]]" for n in nums]


def extract_prs(text: str) -> list[int]:
    """Inteiros únicos de `#NNN` ≥ 5 (filtra footnotes ruidosos)."""
    return sorted({int(m) for m in PR_REF_RE.findall(text) if int(m) >= 5})


def extract_commits(text: str) -> list[str]:
    """Hashes únicos em backticks (`abc1234`), preserva ordem de aparição."""
    seen: set[str] = set()
    out: list[str] = []
    for m in COMMIT_BACKTICK_RE.finditer(text):
        h = m.group(1)
        if h not in seen:
            seen.add(h)
            out.append(h)
    return out


def extract_lane_ref(text: str) -> str | None:
    """Wikilink `[[A10.2]]` se há lane-ref clara no texto."""
    m = LANE_REF_RE.search(text)
    if not m:
        return None
    candidate = m.group(1)
    if re.match(r"^[AFW]\d+\.\d+[a-z]?$", candidate):
        return f"[[{candidate}]]"
    return None


def has_breaking(text: str) -> bool:
    """True se texto contém marker `BREAKING`."""
    return bool(BREAKING_RE.search(text))


# ----------------------------------------------------------------------
# Scope derivation
# ----------------------------------------------------------------------


def derive_scope(*, title: str, lane: str | None, prs: list[int], sprint: str | None) -> str:
    """Scope UPPER+digits+hífen via heurística em ordem; sanitiza no final."""
    raw = _derive_scope_raw(title=title, lane=lane, prs=prs, sprint=sprint)
    return _sanitize_scope(raw)


def _derive_scope_raw(*, title: str, lane: str | None, prs: list[int], sprint: str | None) -> str:
    """Tenta cada regra em ordem; primeira que casa vence."""
    for rule in _SCOPE_RULES:
        result = rule(title=title, lane=lane, prs=prs, sprint=sprint)
        if result:
            return result
    return _short_slug(title) or "MISC"


def _scope_from_lane(*, lane: str | None, **_: object) -> str | None:
    if lane:
        return lane.strip("[]").replace(".", "-").upper()
    return None


def _scope_from_title_lane(*, title: str, **_: object) -> str | None:
    m = re.match(
        r"^(A\d+\.\d+[a-z]?|F\d+\.\d+[a-z]?|W\d+-T\d+|W\d+\.[A-Z]\d+)",
        title.strip("*"),
    )
    return m.group(1).replace(".", "-").upper() if m else None


def _scope_from_pr(*, prs: list[int], **_: object) -> str | None:
    return f"PR{prs[0]}" if prs and len(prs) == 1 else None


def _scope_from_adr(*, title: str, **_: object) -> str | None:
    m = re.match(r"^ADR-(\d{3})\b", title)
    return f"ADR-{m.group(1)}" if m else None


def _scope_from_phase_h2(*, title: str, **_: object) -> str | None:
    m = re.match(r"^\[(F\d+(?:\.\d+)?)\]", title)
    return m.group(1).replace(".", "").upper() if m else None


def _scope_from_conv_commit(*, title: str, **_: object) -> str | None:
    m = re.match(r"^(feat|fix|refactor|chore|docs|test|perf)\(([a-z,]+)\)", title)
    if m:
        kind, area = m.group(1), m.group(2).split(",")[0]
        return f"{kind.upper()}-{area.upper()}"
    m = re.match(r"^(feat|fix|refactor|chore|docs|test|perf):", title)
    return m.group(1).upper() if m else None


def _scope_from_bloco(*, title: str, **_: object) -> str | None:
    m = re.match(r"^Bloco\s+(\d+)", title)
    return f"BLOCO-{m.group(1)}" if m else None


def _scope_from_sprint_slug(*, title: str, sprint: str | None, **_: object) -> str | None:
    if not sprint:
        return None
    return f"{sprint}-{_short_slug(title)}".upper()


# Ordem importa: phase_h2 e adr no título têm prioridade sobre lane no body
# (entry de F-phase legacy `## [F9]` referencia F0.2/F1.1 no corpo, não é lane).
_SCOPE_RULES = (
    _scope_from_phase_h2,
    _scope_from_adr,
    _scope_from_title_lane,
    _scope_from_lane,
    _scope_from_pr,
    _scope_from_conv_commit,
    _scope_from_bloco,
    _scope_from_sprint_slug,
)


def _sanitize_scope(scope: str) -> str:
    """UPPER+digits+hífen apenas; remove pontos/underscores; max 40 chars."""
    scope = scope.upper().replace(".", "").replace("_", "-")
    scope = re.sub(r"[^A-Z0-9-]+", "-", scope)
    scope = re.sub(r"-+", "-", scope).strip("-")
    if len(scope) > 40:
        scope = scope[:40].rstrip("-")
    return scope or "ENTRY"


def _short_slug(text: str) -> str:
    """Slug ASCII ≤20 chars, lowercase, hífens."""
    text = re.sub(r"[^A-Za-z0-9]+", "-", text)
    return text.strip("-")[:20].strip("-") or "ENTRY"
