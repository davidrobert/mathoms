#!/usr/bin/env python3
"""Gate: emenda datada no corpo de ADR exige sinal `amended_at` no frontmatter.

Anti-recorrência do gap sistêmico do audit-vault r6 (ADR-302): 7+ ADRs
tinham `## Emenda 2026-06-18 — ...` no corpo com frontmatter intocado —
leitor de diff/índice não via que a decisão mudou. O sinal canônico
machine-readable é o campo `amended_at: ["YYYY-MM-DD", ...]`
(docs/_schemas/note-adr.schema.json); o blockquote no topo (padrão ADR-027)
segue como recomendação editorial, cobrada pelo audit-vault — não por este
gate (gate de estilo se burla; este prova um invariante único).

Regras de detecção (co-design information-architect, 2026-07-04):
- Headings ``##``–``####`` cujo texto casa (Emenda|Correção|Calibração|
  Errata|Aditamento — como palavra) contam como marcador.
- A data vem do próprio heading ou, se ausente, da 1ª linha não-vazia do
  bloco seguinte (blockquote/parágrafo).
- Heading com wikilink [[ADR-NNN]]/[[PLAN-...]] que NÃO seja o id próprio é
  DESCARTADO — emenda narrada de ADR alheia (ex.: ADR-294 "Emenda a
  [[ADR-292]]") não é emenda desta nota.
- Falha se alguma data detectada > frontmatter `date:` e ausente de
  `amended_at`. Menções inline soltas ficam fora do MVP (ruído).

Stdlib puro — roda no job Lint sem venv completo.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ADR_DIR = REPO_ROOT / "docs" / "adr"

AMENDMENT_HEADING_RE = re.compile(
    r"^(#{2,4})\s+.*\b(Emenda|Correç[aã]o|Calibraç[aã]o|Errata|Aditamento)\b",
    re.IGNORECASE,
)
DATE_RE = re.compile(r"\b(20\d{2}-\d{2}-\d{2})\b")
WIKILINK_RE = re.compile(r"\[\[((?:ADR|PLAN)-[^\]]+)\]\]")
FM_DATE_RE = re.compile(r'^date:\s*"?(20\d{2}-\d{2}-\d{2})"?\s*$', re.MULTILINE)
FM_ID_RE = re.compile(r"^id:\s*(ADR-[\w-]+)\s*$", re.MULTILINE)
AMENDED_AT_BLOCK_RE = re.compile(
    r"^amended_at:\s*\n((?:\s+-\s+.*\n)+)|^amended_at:\s*\[(.*?)\]\s*$",
    re.MULTILINE,
)


def _split_frontmatter(text: str) -> tuple[str, str]:
    if not text.startswith("---"):
        return "", text
    end = text.find("\n---", 3)
    if end == -1:
        return "", text
    return text[3:end], text[end + 4 :]


def _amended_dates_from_frontmatter(fm: str) -> set[str]:
    m = AMENDED_AT_BLOCK_RE.search(fm)
    if not m:
        return set()
    blob = m.group(1) or m.group(2) or ""
    return set(DATE_RE.findall(blob))


def _first_content_line_after(lines: list[str], idx: int) -> str:
    for line in lines[idx + 1 : idx + 4]:
        stripped = line.strip()
        if stripped:
            return stripped
    return ""


def _foreign_wikilink(heading: str, own_id: str) -> bool:
    return any(link != own_id for link in WIKILINK_RE.findall(heading))


def _amendment_dates_in_body(body: str, own_id: str) -> set[str]:
    dates: set[str] = set()
    lines = body.splitlines()
    for idx, line in enumerate(lines):
        if not AMENDMENT_HEADING_RE.match(line):
            continue
        if _foreign_wikilink(line, own_id):
            continue
        m = DATE_RE.search(line) or DATE_RE.search(_first_content_line_after(lines, idx))
        if m:
            dates.add(m.group(1))
    return dates


def _format_error(path: Path, missing: list[str], declared: set[str]) -> str:
    suggestion = (
        "amended_at: [" + ", ".join(f'"{d}"' for d in sorted(declared | set(missing))) + "]"
    )
    try:
        display = str(path.relative_to(REPO_ROOT))
    except ValueError:
        display = str(path)
    return (
        f"{display}: emenda(s) datada(s) {missing} sem sinal no "
        f"frontmatter — adicione `{suggestion}`"
    )


def check_file(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    fm, body = _split_frontmatter(text)
    fm_id = FM_ID_RE.search(fm)
    fm_date = FM_DATE_RE.search(fm)
    if not fm_id or not fm_date:
        return []  # frontmatter incompleto é escopo do validate_frontmatter
    declared = _amended_dates_from_frontmatter(fm)
    missing = [
        d
        for d in sorted(_amendment_dates_in_body(body, fm_id.group(1)))
        if d > fm_date.group(1) and d not in declared
    ]
    if not missing:
        return []
    return [_format_error(path, missing, declared)]


def main(argv: list[str]) -> int:
    targets = [Path(a) for a in argv if a.endswith(".md")] or sorted(ADR_DIR.glob("*.md"))
    errors: list[str] = []
    for path in targets:
        if path.is_file() and "archive" not in path.as_posix():
            errors.extend(check_file(path.resolve()))
    if errors:
        print("\n".join(errors))
        print(f"\n{len(errors)} ADR(s) com emenda sem sinal `amended_at:` (padrão ADR-027).")
        return 1
    print(f"✓ amendment signal OK ({len(targets)} ADRs verificadas).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
