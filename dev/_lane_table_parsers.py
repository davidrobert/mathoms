"""Helpers de parsing de tabelas markdown para dev/migrate_lanes_tables.py."""
# Quebra de linhas em células, classificação de lane row, normalização de IDs.
# Espelha lane regex de docs/_schemas/note-lane.schema.json.

from __future__ import annotations

import re

LANE_COLUMN_NAMES: tuple[str, ...] = ("Lane", "Wave")

TABLE_ROW_RE = re.compile(r"^\|(.+)\|\s*$")
TABLE_SEPARATOR_RE = re.compile(r"^\|[\s\-:|]+\|\s*$")

# Schema regex (espelha note-lane.schema.json) — exige lowercase pós-ponto/hífen.
LANE_ID_SCHEMA_RE = re.compile(r"^[A-Z]\d+[a-z]*(?:-[a-z][a-z0-9-]*)?(?:\.[a-z0-9][a-z0-9-]*)*$")

# Mapeamento explícito raw bold → ID alvo (espelha wikilinks dos `lanes.md` editoriais).
# Apenas sufixo após o `<sprint>.` — sprint é prefixado pelo `qualify_id` se não vier.
_RAW_ID_REWRITES: dict[str, str] = {
    "N3 PR-A": "N3-PR-A",
    "N3 PR-B+C": "N3-PR-BC",
    "A1 (F9.3)": "A1",
    "Bloco 0.6 P2/P3": "0.6-P2-P3",
}


def split_row(line: str) -> list[str]:
    """Quebra `| a | b | c |` em ['a', 'b', 'c'] (strip por célula)."""
    inner = line.strip()
    if inner.startswith("|"):
        inner = inner[1:]
    if inner.endswith("|"):
        inner = inner[:-1]
    return [cell.strip() for cell in inner.split("|")]


def is_lane_row(cells: list[str]) -> bool:
    """True se a primeira célula tem `**<ID>**` reconhecível como lane id."""
    if not cells:
        return False
    return bool(re.match(r"^\*\*[^*]+\*\*", cells[0]))


def extract_id_and_title(first_cell: str) -> tuple[str, str] | None:
    """Extrai (id, title) de `**<bold>**<rest>` — bold pode conter espaços/parens."""
    m = re.match(r"^\*\*([^*]+)\*\*\s*(.*)$", first_cell)
    if not m:
        return None
    return m.group(1).strip(), m.group(2).strip()


def has_lane_column(headers: list[str]) -> bool:
    return any(h in LANE_COLUMN_NAMES for h in headers)


def skip_separator(lines: list[str], idx: int) -> int:
    if idx < len(lines) and TABLE_SEPARATOR_RE.match(lines[idx]):
        return idx + 1
    return idx


def normalize_token(raw: str) -> str:
    """Replace whitespace/`+`/`/` por `-`; remove parens; mantém pontos e letras."""
    cleaned = re.sub(r"\s+", "-", raw.strip())
    cleaned = cleaned.replace("+", "-").replace("/", "-")
    cleaned = re.sub(r"[()]", "", cleaned)
    cleaned = re.sub(r"-+", "-", cleaned).strip("-")
    return cleaned


def qualify_id(raw_id: str, sprint: str) -> str:
    """Prefixa com sprint se necessário; normaliza IDs com espaço/`/`/`+`."""
    fixed = _RAW_ID_REWRITES.get(raw_id)
    if fixed is not None:
        return f"{sprint}.{fixed}"
    if re.match(r"^[AF]\d+\.", raw_id):
        return normalize_token(raw_id)
    if re.match(r"^[A-Z]+\d*[a-z]?$", raw_id):
        return f"{sprint}.{raw_id}"
    return f"{sprint}.{normalize_token(raw_id)}"


def _lowercase_post_sprint(raw_id: str) -> str:
    """Lowercase tudo após o primeiro `<letra><dígitos>` (sprint head)."""
    m = re.match(r"^([A-Z]\d+)(.*)$", raw_id)
    if not m:
        return raw_id.lower()
    return f"{m.group(1)}{m.group(2).lower()}"


def canonicalize(raw_id: str) -> tuple[str, str | None]:
    """Retorna (canonical_id, alias) — alias preserva original se uppercase pós-ponto."""
    if LANE_ID_SCHEMA_RE.match(raw_id):
        return raw_id, None
    canonical = _lowercase_post_sprint(raw_id)
    if not LANE_ID_SCHEMA_RE.match(canonical):
        canonical = _lowercase_post_sprint(raw_id.replace("/", "-"))
    if canonical == raw_id:
        return canonical, None
    return canonical, raw_id


def build_filename(canonical_id: str, slug: str) -> str:
    """Filename = `<id-com-hifen>-<slug>.md` (igual a F4.A H3 lanes)."""
    id_part = canonical_id.replace(".", "-")
    return f"{id_part}-{slug}.md"
