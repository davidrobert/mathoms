#!/usr/bin/env python3
"""Regenera índices materializados em docs/_MOC/_generated/ a partir do frontmatter das notas."""

from __future__ import annotations

import argparse
import difflib
import re
import sys
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS = REPO_ROOT / "docs"
GENERATED_DIR = DOCS / "_MOC" / "_generated"

# Diretórios da vault que NÃO devem ser indexados.
# Inclui o próprio output do codegen (evita auto-referência) e legados que
# permanecem como Markdown plano durante a transição (Fases 2-5 do plano).
SKIP_DIRS: frozenset[str] = frozenset(
    {
        "_MOC",
        "_schemas",
        "archive",
        "agent_prompts",
        "audits",
        "runbooks",
        "api",
    }
)

FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)
SPRINT_DIR_RE = re.compile(r"^([A-Z])(\d+)$")

HEADER_LINES: tuple[str, str] = (
    "> Auto-gerado por `dev/build_doc_index.py`. Não edite manualmente.",
    "> Para regenerar: `python3 dev/build_doc_index.py --inline`.",
)


@dataclass(frozen=True)
class Note:
    """Nota da vault com frontmatter parseado e tipado."""

    path: Path
    id: str
    type: str
    status: str
    title: str
    sprint: str | None = None
    plan: str | None = None
    tags: tuple[str, ...] = ()
    raw: dict[str, Any] = field(default_factory=dict)


def parse_frontmatter(md_path: Path) -> dict[str, Any] | None:
    """Extrai bloco YAML entre `---` no topo do arquivo. None se ausente ou inválido."""
    try:
        text = md_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        print(f"warn: falha ao ler {md_path}: {exc}", file=sys.stderr)
        return None
    match = FRONTMATTER_RE.match(text)
    if not match:
        return None
    try:
        data = yaml.safe_load(match.group(1))
    except yaml.YAMLError as exc:
        print(f"warn: frontmatter YAML inválido em {md_path}: {exc}", file=sys.stderr)
        return None
    if not isinstance(data, dict):
        return None
    return data


def _to_note(md_path: Path, fm: dict[str, Any]) -> Note | None:
    """Converte frontmatter dict em Note. None se faltar campo essencial `type`."""
    type_ = fm.get("type")
    if not isinstance(type_, str) or not type_.strip():
        return None
    tags = fm.get("tags") or []
    tags_tuple = tuple(str(t) for t in tags) if isinstance(tags, list) else ()
    sprint = fm.get("sprint")
    plan = fm.get("plan")
    return Note(
        path=md_path,
        id=str(fm.get("id", "")),
        type=type_,
        status=str(fm.get("status", "")),
        title=str(fm.get("title", "")),
        sprint=str(sprint) if sprint is not None else None,
        plan=str(plan) if plan is not None else None,
        tags=tags_tuple,
        raw=fm,
    )


def _is_skipped(md_path: Path, docs_root: Path) -> bool:
    """True se o arquivo está em diretório legado/gerado que não deve ser indexado."""
    try:
        rel_parts = md_path.relative_to(docs_root).parts
    except ValueError:
        return True
    return bool(rel_parts) and rel_parts[0] in SKIP_DIRS


def collect_notes(docs_root: Path) -> list[Note]:
    """Walk docs/ procurando *.md com frontmatter; pula diretórios em SKIP_DIRS."""
    notes: list[Note] = []
    for md_path in sorted(docs_root.rglob("*.md")):
        if _is_skipped(md_path, docs_root):
            continue
        fm = parse_frontmatter(md_path)
        if fm is None:
            continue
        note = _to_note(md_path, fm)
        if note is not None:
            notes.append(note)
    return notes


def _rel_path(note: Note) -> str:
    """Path relativo a docs/ com forward slashes (estável cross-OS)."""
    return note.path.relative_to(DOCS).as_posix()


def _header(title: str) -> list[str]:
    """Bloco de cabeçalho padrão (header de aviso + título h1)."""
    return [HEADER_LINES[0], HEADER_LINES[1], "", f"# {title}", ""]


def _join(lines: list[str]) -> str:
    """Junta linhas com `\n` e garante trailing newline único."""
    return "\n".join(lines).rstrip() + "\n"


def build_index_md(notes: list[Note]) -> str:
    """Gera INDEX.md — 1 linha por nota em tabela markdown."""
    lines = _header("Índice geral da vault")
    if not notes:
        lines.append("_Nenhuma nota com frontmatter indexada ainda._")
        return _join(lines)
    lines.append("| id | type | status | sprint | título | path |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    for note in sorted(notes, key=lambda n: (n.type, n.id, _rel_path(n))):
        sprint = note.sprint or ""
        lines.append(
            f"| {note.id} | {note.type} | {note.status} | {sprint} "
            f"| {note.title} | `{_rel_path(note)}` |"
        )
    return _join(lines)


# Categorização e renderer ADR_INDEX vivem em _adr_index_renderer.py para manter
# este módulo <500 linhas (guideline CLAUDE.md). F2.F deletará dev/build_adr_toc.py.
try:
    from _adr_index_renderer import (  # noqa: E402
        _load_adr_categories,
        category_for_adr,
        render_adr_index,
    )
except ModuleNotFoundError:  # pragma: no cover
    from dev._adr_index_renderer import (  # noqa: E402
        _load_adr_categories,
        category_for_adr,
        render_adr_index,
    )


def build_adr_index_md(notes: list[Note]) -> str:
    """Gera ADR_INDEX.md — ADRs agrupadas por categoria + status com sumário."""
    adrs = [n for n in notes if n.type == "adr"]
    return _join(render_adr_index(adrs, _header))


def _detect_current_sprint(docs_root: Path) -> str | None:
    """Diretório `docs/sprint/<X>/` com maior número (ex.: `A11` > `A10`)."""
    sprint_root = docs_root / "sprint"
    if not sprint_root.is_dir():
        return None
    candidates: list[tuple[str, int, str]] = []
    for child in sprint_root.iterdir():
        if not child.is_dir():
            continue
        match = SPRINT_DIR_RE.match(child.name)
        if not match:
            continue
        candidates.append((match.group(1), int(match.group(2)), child.name))
    if not candidates:
        return None
    return max(candidates, key=lambda c: (c[0], c[1]))[2]


def _format_lane_rows(lanes: list[Note]) -> list[str]:
    """Constrói as linhas de tabela para um conjunto de lanes ordenadas por id."""
    rows = ["| id | status | priority | título | path |", "| --- | --- | --- | --- | --- |"]
    for note in sorted(lanes, key=lambda n: n.id):
        priority = str(note.raw.get("priority", ""))
        rows.append(
            f"| {note.id} | {note.status} | {priority} | {note.title} | `{_rel_path(note)}` |"
        )
    return rows


def build_sprint_current_md(notes: list[Note]) -> str:
    """Gera SPRINT_CURRENT.md — lanes da sprint corrente; stub se nenhuma sprint indexada."""
    lines = _header("Sprint corrente — lanes ativas")
    current = _detect_current_sprint(DOCS)
    if current is None:
        lines.append("_Nenhuma sprint indexada (Fase 4 do plano popula `docs/sprint/`)._")
        return _join(lines)
    lines.append(f"_Sprint detectada: **{current}**._")
    lines.append("")
    lanes = [n for n in notes if n.type == "lane" and n.sprint == current]
    if not lanes:
        lines.append("_Nenhuma lane com frontmatter na sprint corrente ainda._")
        return _join(lines)
    lines.extend(_format_lane_rows(lanes))
    return _join(lines)


def _entry_date(note: Note) -> date | None:
    """Lê `date:` do frontmatter e normaliza para `datetime.date`."""
    raw = note.raw.get("date")
    if isinstance(raw, date) and not isinstance(raw, datetime):
        return raw
    if isinstance(raw, datetime):
        return raw.date()
    if isinstance(raw, str):
        try:
            return datetime.strptime(raw, "%Y-%m-%d").date()
        except ValueError:
            return None
    return None


def _group_entries_by_day(entries: list[Note], cutoff: date) -> dict[date, list[Note]]:
    """Agrupa entradas com `date >= cutoff` por dia. Entradas sem data válida são ignoradas."""
    by_day: dict[date, list[Note]] = {}
    for note in entries:
        d = _entry_date(note)
        if d is None or d < cutoff:
            continue
        by_day.setdefault(d, []).append(note)
    return by_day


def _render_changelog_days(by_day: dict[date, list[Note]]) -> list[str]:
    """Renderiza dias em ordem decrescente, com entries ordenados por id."""
    out: list[str] = []
    for day in sorted(by_day, reverse=True):
        out.append(f"## {day.isoformat()}")
        out.append("")
        for note in sorted(by_day[day], key=lambda n: n.id):
            out.append(f"- **{note.id}** — {note.title} (`{_rel_path(note)}`)")
        out.append("")
    return out


def build_changelog_recent_md(notes: list[Note]) -> str:
    """Gera CHANGELOG_RECENT.md — entries dos últimos 14 dias agregados por dia."""
    lines = _header("Changelog — últimos 14 dias")
    entries = [n for n in notes if n.type == "changelog-entry"]
    if not entries:
        lines.append(
            "_Nenhuma entrada de changelog na vault ainda "
            "(Fase 5 do plano popula `docs/sprint/<X>/changelog/`)._"
        )
        return _join(lines)
    by_day = _group_entries_by_day(entries, date.today() - timedelta(days=14))
    if not by_day:
        lines.append("_Sem entradas nos últimos 14 dias._")
        return _join(lines)
    lines.extend(_render_changelog_days(by_day))
    return _join(lines)


def build_roadmap_md(notes: list[Note]) -> str:
    """Gera ROADMAP.md — tabela F0-F11; stub mínimo até Fase 5 do plano."""
    lines = _header("Roadmap F0-F11")
    lines.append("_Tabela populada na Fase 5 do plano (extração de `docs/reference/PHASES.md`)._")
    return _join(lines)


def _plan_progress_row(plan_id: str, entries: list[Note]) -> str:
    """Conta lanes por status conhecido e formata uma linha da tabela de progresso."""
    shipped = sum(1 for n in entries if n.status == "shipped")
    in_progress = sum(1 for n in entries if n.status == "in_progress")
    open_ = sum(1 for n in entries if n.status == "open")
    others = len(entries) - shipped - in_progress - open_
    return f"| {plan_id} | {len(entries)} | {shipped} | {in_progress} | {open_} | {others} |"


def build_plan_progress_md(notes: list[Note]) -> str:
    """Gera PLAN_PROGRESS.md — agrega lanes por plano (campo `plan:` do frontmatter)."""
    lines = _header("Progresso por plano multi-fase")
    lanes = [n for n in notes if n.type == "lane" and n.plan]
    if not lanes:
        lines.append("_Nenhuma lane com `plan:` declarado ainda (Fases 3-4 do plano popularão)._")
        return _join(lines)
    by_plan: dict[str, list[Note]] = {}
    for note in lanes:
        assert note.plan is not None
        by_plan.setdefault(note.plan, []).append(note)
    lines.append("| plano | total | shipped | in_progress | open | outras |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    for plan_id in sorted(by_plan):
        lines.append(_plan_progress_row(plan_id, by_plan[plan_id]))
    return _join(lines)


def regenerate_all(docs_root: Path) -> dict[str, str]:
    """Retorna `{filename: content}` para os 6 arquivos materializados."""
    notes = collect_notes(docs_root)
    return {
        "INDEX.md": build_index_md(notes),
        "ADR_INDEX.md": build_adr_index_md(notes),
        "SPRINT_CURRENT.md": build_sprint_current_md(notes),
        "CHANGELOG_RECENT.md": build_changelog_recent_md(notes),
        "ROADMAP.md": build_roadmap_md(notes),
        "PLAN_PROGRESS.md": build_plan_progress_md(notes),
    }


def write_files(target_dir: Path, content_by_name: dict[str, str]) -> list[str]:
    """Escreve arquivos no disco; retorna lista dos que mudaram."""
    target_dir.mkdir(parents=True, exist_ok=True)
    changed: list[str] = []
    for name, content in content_by_name.items():
        path = target_dir / name
        existing = path.read_text(encoding="utf-8") if path.exists() else None
        if existing != content:
            path.write_text(content, encoding="utf-8")
            changed.append(name)
    return changed


def _file_drift(name: str, content: str) -> tuple[str, str] | None:
    """Compara um arquivo gerado vs disco. Retorna `(name, diff)` se difere, senão None."""
    path = GENERATED_DIR / name
    if not path.exists():
        return name, f"(ausente — esperado {len(content)} bytes)"
    actual = path.read_text(encoding="utf-8")
    if actual == content:
        return None
    diff = "".join(
        difflib.unified_diff(
            actual.splitlines(keepends=True),
            content.splitlines(keepends=True),
            fromfile=f"a/docs/_MOC/_generated/{name}",
            tofile=f"b/docs/_MOC/_generated/{name}",
            n=2,
        )
    )
    return name, diff


def check_drift(docs_root: Path) -> tuple[bool, list[tuple[str, str]]]:
    """Compara disco vs regenerado. Retorna `(has_drift, [(filename, diff), ...])`."""
    expected = regenerate_all(docs_root)
    drifted = [d for d in (_file_drift(n, c) for n, c in expected.items()) if d is not None]
    return bool(drifted), drifted


def _print_drift(drifted: list[tuple[str, str]]) -> None:
    """Imprime mensagem de erro + diffs em stderr."""
    print(
        "✗ docs/_MOC/_generated/ fora de sync. Rode "
        "`python3 dev/build_doc_index.py --inline` e commite o diff.",
        file=sys.stderr,
    )
    for name, diff in drifted:
        print(f"\n--- drift em {name} ---", file=sys.stderr)
        print(diff or "(diff vazio)", file=sys.stderr)


def _run_check() -> int:
    if not GENERATED_DIR.exists():
        print(
            f"erro: {GENERATED_DIR.relative_to(REPO_ROOT)} não existe. "
            "Rode `python3 dev/build_doc_index.py --inline` primeiro.",
            file=sys.stderr,
        )
        return 1
    has_drift, drifted = check_drift(DOCS)
    if not has_drift:
        print("✓ docs/_MOC/_generated/ sincronizado com a vault.")
        return 0
    _print_drift(drifted)
    return 1


def _run_inline() -> int:
    expected = regenerate_all(DOCS)
    changed = write_files(GENERATED_DIR, expected)
    if changed:
        print(f"✓ regenerado: {', '.join(changed)}")
    else:
        print("✓ docs/_MOC/_generated/ já sincronizado (nenhuma mudança).")
    return 0


def _run_self_test() -> int:
    """Roda smoke tests inline (definidos em _test_build_doc_index_smoke.py)."""
    try:
        from _test_build_doc_index_smoke import run_smoke_tests
    except ModuleNotFoundError:  # pragma: no cover
        from dev._test_build_doc_index_smoke import run_smoke_tests
    return run_smoke_tests(
        note_cls=Note,
        build_fn=build_adr_index_md,
        load_fn=_load_adr_categories,
        category_fn=category_for_adr,
    )


def _build_parser() -> argparse.ArgumentParser:
    """Define a CLI com flags `--check`, `--inline` e `--self-test` mutuamente exclusivas."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit 1 se _MOC/_generated/ está fora de sync",
    )
    parser.add_argument(
        "--inline",
        action="store_true",
        help="regenera in-place sobrescrevendo os 6 arquivos",
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="roda smoke tests inline da categorização de ADRs",
    )
    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    flags_set = sum(int(f) for f in (args.check, args.inline, args.self_test))
    if flags_set > 1:
        print("erro: --check, --inline e --self-test são mutuamente exclusivas.", file=sys.stderr)
        return 2
    if args.check:
        return _run_check()
    if args.inline:
        return _run_inline()
    if args.self_test:
        return _run_self_test()
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
